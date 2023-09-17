import json

from mypy_boto3_iam.client import IAMClient
from mypy_boto3_iam.service_resource import IAMServiceResource, InstanceProfile

from holy_cli.config import Config

from .base import BaseWrapper

POLICY_PATH_PREFIX = "/holy/"
POLICY_INLINE_NAME = "holy-custom-policy"


class IAMWrapper(BaseWrapper):
    """Encapsulates Amazon IAM actions."""

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        session = self.init_boto3_session()
        self.iam: IAMServiceResource = session.resource("iam")

    def create_instance_profile(self, server_id: str, actions: str) -> InstanceProfile:
        role_name = f"holy-role-{server_id}"
        tags = self.get_tags(None, {"holy-cli:server": server_id})

        role = self.iam.create_role(
            RoleName=role_name,
            Path=POLICY_PATH_PREFIX,
            AssumeRolePolicyDocument=self._get_trust_ec2_policy(),
            Tags=tags,  # type: ignore
        )

        role_policy = self.iam.RolePolicy(role.name, POLICY_INLINE_NAME)
        role_policy.put(PolicyDocument=self._get_custom_policy(actions))

        profile = self.iam.create_instance_profile(
            InstanceProfileName=role.name, Tags=tags  # type: ignore
        )
        profile.add_role(RoleName=role.name)

        return profile

    def _get_trust_ec2_policy(self) -> str:
        return json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "ec2.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        )

    def _get_custom_policy(self, actions: str) -> str:
        actions_list = [action.strip() for action in actions.split(",")]

        return json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": actions_list, "Resource": "*"}
                ],
            }
        )

    def teardown(self) -> None:
        roles = list(self.iam.roles.filter(PathPrefix=POLICY_PATH_PREFIX))

        for role in roles:
            for profile in list(role.instance_profiles.all()):
                profile.remove_role(RoleName=role.name)
                profile.delete()

            for policy in list(role.policies.all()):
                policy.delete()

            role.delete()

    def delete(self, server_id: str) -> None:
        session = self.init_boto3_session()
        client: IAMClient = session.client("iam")
        role_name = f"holy-role-{server_id}"

        client.remove_role_from_instance_profile(
            InstanceProfileName=role_name, RoleName=role_name
        )
        client.delete_instance_profile(InstanceProfileName=role_name)
        client.delete_role_policy(RoleName=role_name, PolicyName=POLICY_INLINE_NAME)
        client.delete_role(RoleName=role_name)
