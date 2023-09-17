from __future__ import annotations

import time
from typing import List, Optional

from botocore.exceptions import ClientError
from mypy_boto3_ec2.service_resource import Instance
from yaspin import yaspin

from holy_cli.config import Config, GlobalConfig
from holy_cli.exceptions import AbortError
from holy_cli.log import getLogger

from ..options import CreateServerOptions, ServerDTO
from . import AWS_OS_USER_MAPPING
from .iam import IAMWrapper
from .image import ImageWrapper
from .instance import InstanceWrapper
from .key_pair import KeyPairWrapper
from .security_group import SecurityGroupWrapper
from .ssh import SSHWrapper
from .vpc import VPCWrapper


class AWSActions:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.log = getLogger()
        self.vpc = VPCWrapper(self.config)
        self.key_pair = KeyPairWrapper(self.config)
        self.image = ImageWrapper(self.config)
        self.security_group = SecurityGroupWrapper(self.config)
        self.iam = IAMWrapper(self.config)
        self.instance = InstanceWrapper(self.config)

    def teardown(self) -> None:
        def teardown_retry(attempts: int) -> None:
            self.log.debug(f"Teardown attempt #{attempts}")

            try:
                self.security_group.teardown()
                self.key_pair.teardown()
                self.iam.teardown()
                self.vpc.teardown()
            except ClientError as err:
                if err.response["Error"]["Code"] == "DependencyViolation":
                    if attempts < 10:
                        time.sleep(5)
                        teardown_retry(attempts + 1)
                        return
                raise

        with yaspin(text="Removing infrastructure", color="yellow") as spinner:
            try:
                self.instance.teardown()
                teardown_retry(0)

                spinner.ok("✅ ")
            except:
                spinner.fail("💥 ")
                raise

    def create_server(self, options: CreateServerOptions) -> Instance:
        self.log.info(f"Creating server {options.name} with ID {options.id}")

        with yaspin(text=f"Creating server {options.name}", color="yellow") as spinner:
            try:
                if self.instance.exists(options.id):
                    raise AbortError(
                        "Server already exists, please choose a different name"
                    )

                vpc = None
                subnet = None

                # Use provided subnet / VPC
                if options.subnet_id:
                    subnet = self.vpc.get_subnet(options.subnet_id)

                    if subnet is None:
                        raise AbortError("Subnet not found")

                    vpc = subnet.vpc
                else:
                    # Create or use holy VPC
                    vpc = self.vpc.get_vpc()

                    if vpc is None:
                        vpc = self.vpc.create()
                        spinner.write("> Created VPC")

                    subnet = list(vpc.subnets.all())[0]

                self.log.info(f"VPC ID: {vpc.id}")
                self.log.info(f"Subnet ID: {subnet.id}")

                # Create a new key pair
                key_pair = self.key_pair.create(options.id)
                self.log.info(f"Key pair name: {key_pair.name}")
                spinner.write("> Created key pair")

                # Use the specified AMI image or find one based on the OS and architecture
                if options.image_id:
                    image_id = options.image_id
                else:
                    image_id = self.image.find_image_id(
                        options.os, options.architecture
                    )
                    self.log.info(f"Image ID: {image_id}")
                    spinner.write("> Found AMI image")

                # Create a new security group
                sg = self.security_group.create(
                    vpc.id, options.id, options.name, options.ports
                )
                self.log.info(f"Security group ID: {sg.id}")
                spinner.write("> Created security group")

                # Create a new IAM role and instance profile
                iam_profile_for_actions = None

                if options.actions and not options.iam_profile:
                    iam_profile_for_actions = self.iam.create_instance_profile(
                        options.id, options.actions
                    )
                    self.log.info(f"IAM profile ARN: {iam_profile_for_actions.arn}")
                    spinner.write("> Created IAM role")

                try:
                    instance = self.instance.create(
                        server_id=options.id,
                        server_name=options.name,
                        os=options.os,
                        subnet_id=subnet.id,
                        image_id=image_id,
                        instance_type=options.type,
                        key_pair_name=key_pair.name,
                        security_group_id=sg.id,
                        disk_size=options.disk_size,
                        script_file=options.script_file,
                        iam_profile=options.iam_profile,
                    )

                    self.log.info(f"Instance ID: {instance.id}")
                except ClientError:
                    # Remove anything created at this stage so not to cause name conflicts
                    key_pair.delete()
                    self.key_pair.delete_key_file(key_pair.name)
                    sg.delete()

                    if iam_profile_for_actions:
                        self.iam.delete(options.id)

                    raise

                spinner.write("> Created instance")
                spinner.write("> Waiting for instance to start...")
                instance.wait_until_running()

                # Attach the IAM instance profile once running because it takes several seconds for the permissions to propagate
                if iam_profile_for_actions:
                    self.instance.associate_iam_instance_profile(
                        instance.id, iam_profile_for_actions.arn
                    )
                    spinner.write("> Attached IAM role")

                # Reload the instance data so that we can get the public IP and DNS
                instance.reload()

                spinner.ok("✅ ")
            except:
                spinner.fail("💥 ")
                raise

        return instance

    def get_server_info(self, server: ServerDTO) -> dict:
        instance = self.instance.get_by_id(server.id)
        name = self.instance.get_tag_value(instance.tags, "Name")
        os = self.instance.get_tag_value(instance.tags, "holy-cli:os")

        if instance.state["Name"] != "terminated":
            _, key_file_path = self.key_pair.get_name_and_path(server.id)
        else:
            key_file_path = "-"

        if os in AWS_OS_USER_MAPPING:
            username = AWS_OS_USER_MAPPING[os]
        else:
            username = "-"

        volume_size = "-"
        ports = []

        if len(instance.block_device_mappings) > 0:
            volume_id = instance.block_device_mappings[0]["Ebs"]["VolumeId"]
            volume = self.instance.get_volume(volume_id)

            if volume:
                volume_size = f"{volume.size}GB"

        if len(instance.security_groups) > 0:
            sg = self.security_group.get_by_server_id(server.id)

            if sg:
                ports = [perm["FromPort"] for perm in list(sg.ip_permissions)]
                ports.sort()

        return {
            "AWS ID": instance.id,
            "Holy ID": server.id,
            "Name": name,
            "State": instance.state["Name"],
            "Availability Zone": instance.placement["AvailabilityZone"],
            "OS": os or "-",
            "Architecture": instance.architecture,
            "Type": instance.instance_type,
            "Disk Size": volume_size,
            "Open Ports": ", ".join(map(str, ports)),
            "Public IP": instance.public_ip_address or "-",
            "Private IP": instance.private_ip_address or "-",
            "DNS": instance.public_dns_name or "-",
            "SSH Username": username,
            "SSH Key": key_file_path,
        }

    def list_servers(self, only_running: bool) -> List[dict]:
        results = []
        instances = self.instance.get_all()

        for instance in instances:
            if only_running and instance.state["Name"] != "running":
                continue

            name = self.instance.get_tag_value(instance.tags, "Name")
            os = self.instance.get_tag_value(instance.tags, "holy-cli:os")

            results.append(
                {
                    "Name": name,
                    "State": instance.state["Name"],
                    "OS": os or "-",
                    "Type": instance.instance_type,
                    "IP": instance.public_ip_address or "-",
                    "DNS": instance.public_dns_name or "-",
                }
            )

        if len(results) == 0:
            results.append(
                {
                    "Name": "No existing servers",
                }
            )

        return results

    def ssh_into_server(
        self, server: ServerDTO, username: Optional[str], save: bool
    ) -> None:
        instance = self.instance.get_by_id(server.id)
        _, key_file_path = self.key_pair.get_name_and_path(server.id)

        ssh = SSHWrapper(self.config)

        if save:
            ssh.save_to_file(instance, key_file_path, username)
        else:
            ssh.ssh_into_instance(instance, key_file_path, username)

    def start_server(self, server: ServerDTO) -> None:
        with yaspin(text=f"Starting server {server.name}", color="yellow") as spinner:
            try:
                instance = self.instance.get_by_id(server.id)
                instance.start()
                instance.wait_until_running()

                spinner.ok("✅ ")
            except:
                spinner.fail("💥 ")
                raise

    def stop_server(self, server: ServerDTO) -> None:
        with yaspin(text=f"Stopping server {server.name}", color="yellow") as spinner:
            try:
                instance = self.instance.get_by_id(server.id)
                instance.stop()
                instance.wait_until_stopped()

                spinner.ok("✅ ")
            except:
                spinner.fail("💥 ")
                raise

    def delete_server(self, server: ServerDTO) -> None:
        with yaspin(text=f"Deleting server {server.name}", color="yellow") as spinner:
            try:
                instance = self.instance.get_by_id(server.id)
                instance.terminate()
                instance.wait_until_terminated()
                spinner.write("> Deleted instance")

                key_pair = self.key_pair.get_by_server_id(server.id)

                if key_pair is not None:
                    key_pair.delete()
                    self.key_pair.delete_key_file(key_pair.name)
                    spinner.write("> Deleted key pair")

                sg = self.security_group.get_by_server_id(server.id)

                if sg is not None:
                    sg.delete()
                    spinner.write("> Deleted security group")

                if (
                    instance.iam_instance_profile is not None
                    and "holy-role" in instance.iam_instance_profile["Arn"]
                ):
                    self.iam.delete(server.id)
                    spinner.write("> Deleted IAM role")

                spinner.ok("✅ ")
            except:
                spinner.fail("💥 ")
                raise

    def change_port(
        self, server: ServerDTO, port: int, action: str, ip_source: Optional[str]
    ) -> None:
        instance = self.instance.get_by_id(server.id)
        self.security_group.change_port(server.id, port, action, ip_source)

    @classmethod
    def load_from_cli(cls, region: Optional[str], profile: Optional[str]) -> AWSActions:
        global_config = GlobalConfig()
        config = Config(global_config, region, profile)

        return cls(config)
