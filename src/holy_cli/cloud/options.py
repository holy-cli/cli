from __future__ import annotations

from typing import Optional

from holy_cli.cloud.aws import AWS_ARCHITECTURE_VALUES, AWS_OS_USER_MAPPING
from holy_cli.exceptions import AbortError
from holy_cli.util import get_random_name, hash_server_name


class ServerDTO:
    def __init__(self, name: str) -> None:
        self.name = name.strip()
        self.id = hash_server_name(self.name.lower())


class CreateServerOptions(ServerDTO):
    def __init__(
        self,
        name: str,
        os: Optional[str],
        architecture: Optional[str],
        image_id: Optional[str],
        type: str,
        disk_size: int,
        ports: Optional[str],
        actions: Optional[str],
        script_file: Optional[str],
        iam_profile: Optional[str],
        subnet_id: Optional[str],
    ) -> None:
        super().__init__(name)
        self.os = os
        self.architecture = architecture
        self.image_id = image_id
        self.type = type
        self.disk_size = disk_size
        self.ports = ports
        self.actions = actions
        self.script_file = script_file
        self.iam_profile = iam_profile
        self.subnet_id = subnet_id

    @classmethod
    def load_from_cli(cls, **kwargs) -> CreateServerOptions:
        image_id = kwargs.get("image_id")

        if image_id is None:
            os = kwargs.get("os")
            architecture = kwargs.get("architecture")

            if os not in AWS_OS_USER_MAPPING:
                raise AbortError(
                    "Invalid OS value, must be one of: "
                    + ", ".join(AWS_OS_USER_MAPPING.keys())
                )

            if architecture not in AWS_ARCHITECTURE_VALUES:
                raise AbortError(
                    "Invalid architecture value, must be one of: "
                    + ", ".join(AWS_ARCHITECTURE_VALUES)
                )
        else:
            os = None
            architecture = None

        return cls(
            name=(kwargs.get("name") or get_random_name()),
            os=os,
            architecture=architecture,
            image_id=image_id,
            type=kwargs["type"],
            disk_size=int(kwargs["disk_size"]),
            ports=kwargs.get("ports"),
            actions=kwargs.get("actions"),
            script_file=kwargs.get("script"),
            iam_profile=kwargs.get("iam_profile"),
            subnet_id=kwargs.get("subnet_id"),
        )
