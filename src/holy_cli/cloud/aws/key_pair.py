import os
from typing import Optional, Tuple

from mypy_boto3_ec2.service_resource import KeyPair, KeyPairInfo

from .base import AWS_TAG_KEY, AWS_TAG_VALUE, BaseWrapper


class KeyPairWrapper(BaseWrapper):
    """Encapsulates Amazon EC2 key pair actions."""

    def teardown(self) -> None:
        results = list(
            self.ec2.key_pairs.filter(
                Filters=[{"Name": f"tag:{AWS_TAG_KEY}", "Values": [AWS_TAG_VALUE]}]
            )
        )

        for key_pair in results:
            self.log.debug(f"Deleting key pair {key_pair.name}")
            key_pair.delete()
            self.delete_key_file(key_pair.name)

    def get_name_and_path(self, server_id: str) -> Tuple[str, str]:
        key_name = f"holy-kp-{server_id}"
        key_file_path = self._get_path(key_name)

        return key_name, key_file_path

    def create(self, server_id: str) -> KeyPair:
        key_name, key_file_path = self.get_name_and_path(server_id)

        self.log.debug(f"Creating key pair {key_name}")
        key_pair = self.ec2.create_key_pair(
            KeyName=key_name,
            TagSpecifications=self.get_tags_for_resource(
                "key-pair", None, {"holy-cli:server": server_id}
            ),
        )

        with open(key_file_path, "w") as key_file:
            key_file.write(key_pair.key_material)

        try:
            os.chmod(key_file_path, 0o400)
        except:
            self.log.warning(f"Could not CHMOD key pair file - {key_file_path}")

        return key_pair

    def get_by_server_id(self, server_id: str) -> Optional[KeyPairInfo]:
        results = list(
            self.ec2.key_pairs.filter(
                Filters=[{"Name": "tag:holy-cli:server", "Values": [server_id]}]
            )
        )

        if len(results) > 0:
            return results[0]

    def delete_key_file(self, key_name: str) -> None:
        key_file_path = self._get_path(key_name)

        if os.path.exists(key_file_path):
            os.remove(key_file_path)

    def _get_path(self, key_name: str) -> str:
        return os.path.join(self.config.global_config.keys_dir, f"{key_name}.pem")
