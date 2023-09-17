from typing import List, Optional

from mypy_boto3_ec2.client import EC2Client
from mypy_boto3_ec2.service_resource import Instance, Volume
from mypy_boto3_ec2.type_defs import IamInstanceProfileSpecificationTypeDef

from holy_cli.exceptions import AbortError

from .base import AWS_TAG_KEY, AWS_TAG_VALUE, BaseWrapper


class InstanceWrapper(BaseWrapper):
    """Encapsulates Amazon EC2 instance actions."""

    def create(
        self,
        server_id: str,
        server_name: str,
        os: Optional[str],
        subnet_id: str,
        image_id: str,
        instance_type: str,
        key_pair_name: str,
        security_group_id: str,
        disk_size: int,
        script_file: Optional[str],
        iam_profile: Optional[str],
    ) -> Instance:
        user_data = self._get_script_file(script_file) if script_file else ""
        additional_tags = {"holy-cli:server": server_id}

        if os is not None:
            additional_tags["holy-cli:os"] = os

        iam_instance_profile: IamInstanceProfileSpecificationTypeDef = {}

        if iam_profile is not None:
            if iam_profile.startswith("arn:"):
                iam_instance_profile["Arn"] = iam_profile
            else:
                iam_instance_profile["Name"] = iam_profile

        instance = self.ec2.create_instances(
            ImageId=image_id,
            InstanceType=instance_type,  # type: ignore
            KeyName=key_pair_name,
            MinCount=1,
            MaxCount=1,
            IamInstanceProfile=iam_instance_profile,
            TagSpecifications=self.get_tags_for_resource(
                "instance", server_name, additional_tags
            ),
            BlockDeviceMappings=[
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {"DeleteOnTermination": True, "VolumeSize": disk_size},
                }
            ],
            NetworkInterfaces=[
                {
                    "SubnetId": subnet_id,
                    "DeviceIndex": 0,
                    "AssociatePublicIpAddress": True,
                    "Groups": [security_group_id],
                }
            ],
            UserData=user_data,
        )[0]

        return instance

    def get_by_id(self, server_id: str) -> Instance:
        results = list(
            self.ec2.instances.filter(
                Filters=[{"Name": "tag:holy-cli:server", "Values": [server_id]}]
            )
        )

        if len(results) > 0:
            return results[0]

        raise AbortError("Could not find server")

    def exists(self, server_id: str) -> bool:
        try:
            self.get_by_id(server_id)
            return True
        except AbortError:
            return False

    def get_all(self) -> List[Instance]:
        return list(
            self.ec2.instances.filter(
                Filters=[{"Name": f"tag:{AWS_TAG_KEY}", "Values": [AWS_TAG_VALUE]}]
            )
        )

    def get_volume(self, volume_id: str) -> Optional[Volume]:
        results = list(self.ec2.volumes.filter(VolumeIds=[volume_id]))

        if len(results) > 0:
            return results[0]

    def associate_iam_instance_profile(
        self, instance_id: str, profile_arn: str
    ) -> None:
        session = self.init_boto3_session()
        client: EC2Client = session.client("ec2")
        client.associate_iam_instance_profile(
            InstanceId=instance_id, IamInstanceProfile={"Arn": profile_arn}
        )

    def teardown(self) -> None:
        instances = self.get_all()

        for instance in instances:
            self.log.debug(f"Deleting instance {instance.id}")
            instance.terminate()

    def _get_script_file(self, file: str) -> str:
        with open(file, "r") as f:
            contents = f.read()

        contents = contents.strip()

        if contents[0:2] != "#!":
            contents = "#!/bin/bash\n" + contents

        return contents
