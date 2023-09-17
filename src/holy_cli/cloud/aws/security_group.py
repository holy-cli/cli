from typing import Optional, Sequence

from mypy_boto3_ec2.service_resource import SecurityGroup
from mypy_boto3_ec2.type_defs import IpPermissionTypeDef

from holy_cli.exceptions import AbortError

from .base import AWS_TAG_KEY, AWS_TAG_VALUE, BaseWrapper


class SecurityGroupWrapper(BaseWrapper):
    """Encapsulates Amazon Elastic Compute Cloud (Amazon EC2) security group actions."""

    def teardown(self) -> None:
        results = list(
            self.ec2.security_groups.filter(
                Filters=[{"Name": f"tag:{AWS_TAG_KEY}", "Values": [AWS_TAG_VALUE]}]
            )
        )

        for sg in results:
            self.log.debug(f"Deleting security group {sg.group_name}")
            sg.delete()

    def create(
        self, vpc_id: str, server_id: str, server_name: str, ports: Optional[str]
    ) -> SecurityGroup:
        group_name = f"holy-sg-{server_id}"
        self.log.debug(f"Creating security group {group_name}")

        security_group = self.ec2.create_security_group(
            VpcId=vpc_id,
            GroupName=group_name,
            Description=f"Security group for {server_name} created with holy-cli",
            TagSpecifications=self.get_tags_for_resource(
                "security-group", group_name, {"holy-cli:server": server_id}
            ),
        )

        ip_permissions: Sequence[IpPermissionTypeDef] = []

        if ports:
            for port in ports.split(","):
                port = int(port.strip())

                if port == 0:
                    continue

                ip_permissions.append(
                    {
                        "IpProtocol": "tcp",
                        "FromPort": port,
                        "ToPort": port,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    }
                )

        if len(ip_permissions) > 0:
            security_group.authorize_ingress(IpPermissions=ip_permissions)

        return security_group

    def get_by_server_id(self, server_id: str) -> Optional[SecurityGroup]:
        results = list(
            self.ec2.security_groups.filter(
                Filters=[{"Name": "tag:holy-cli:server", "Values": [server_id]}]
            )
        )

        if len(results) > 0:
            return results[0]

    def change_port(
        self, server_id: str, port: int, action: str, ip_source: Optional[str]
    ) -> None:
        sg = self.get_by_server_id(server_id)

        if sg is None:
            raise AbortError("Could not find security group")

        if ip_source is None:
            ip_source = "0.0.0.0/0"
        elif "/" not in ip_source:
            ip_source = f"{ip_source}/32"

        for perm in list(sg.ip_permissions):
            if perm["FromPort"] == port:
                for ip_range in perm["IpRanges"]:
                    if ip_range["CidrIp"] == ip_source:
                        sg.revoke_ingress(
                            CidrIp=ip_range["CidrIp"],
                            FromPort=perm["FromPort"],
                            ToPort=perm["ToPort"],
                            IpProtocol="tcp",
                        )

        if action == "open":
            sg.authorize_ingress(
                CidrIp=ip_source, FromPort=port, ToPort=port, IpProtocol="tcp"
            )
