from datetime import datetime

from mypy_boto3_ssm.client import SSMClient

from holy_cli.config import Config
from holy_cli.exceptions import AbortError

from .base import BaseWrapper


class ImageWrapper(BaseWrapper):
    """Encapsulates Amazon EC2 AMI image actions."""

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        session = self.init_boto3_session()
        self.ssm: SSMClient = session.client("ssm")

    def find_image_id(self, os: str, architecture: str) -> str:
        if os == "amazon-linux":
            return self._find_amazon_linux_image_id(architecture)

        if os.startswith("ubuntu"):
            return self._find_ubuntu_image_id(os, architecture)

        if os.startswith("rhel"):
            return self._find_redhat_image_id(os, architecture)

        raise AbortError("OS not recognised")

    def _find_amazon_linux_image_id(self, architecture: str) -> str:
        param_path = "/aws/service/ami-amazon-linux-latest"
        ami_paginator = self.ssm.get_paginator("get_parameters_by_path")
        ami_options = []

        self.log.debug(f"Looking up SSM param path {param_path}")
        for page in ami_paginator.paginate(Path=param_path):
            ami_options += page["Parameters"]

        image_ids = [
            opt["Value"]
            for opt in ami_options
            if "default" in opt["Name"] and "minimal" not in opt["Name"]
        ]

        images = list(
            self.ec2.images.filter(
                ImageIds=image_ids,
                Filters=[{"Name": "architecture", "Values": [architecture]}],
            )
        )
        self.log.debug(f"Found {len(images)} amazon linux images")

        if len(images) == 0:
            raise AbortError("Could not find default Amazon Linux image")

        image = images[0]
        self.log.debug(f"Chose {image.name} - {image.description}")

        return image.id

    def _find_ubuntu_image_id(self, os: str, architecture: str) -> str:
        if architecture == "x86_64":
            architecture = "amd64"

        version = os.split(":")[1]
        version = f"{version}.04"

        param_name = f"/aws/service/canonical/ubuntu/server/{version}/stable/current/{architecture}/hvm/ebs-gp2/ami-id"
        self.log.debug(f"Looking up SSM param name {param_name}")

        try:
            result = self.ssm.get_parameter(Name=param_name)
        except:
            raise AbortError("Could not find default Ubuntu image")

        return result["Parameter"]["Value"]

    def _find_redhat_image_id(self, os: str, architecture: str) -> str:
        version = os.split(":")[1]

        images = list(
            self.ec2.images.filter(
                Owners=["309956199498"],
                Filters=[
                    {"Name": "name", "Values": [f"RHEL-{version}.*"]},
                    {"Name": "virtualization-type", "Values": ["hvm"]},
                    {"Name": "architecture", "Values": [architecture]},
                ],
            )
        )
        self.log.debug(f"Found {len(images)} RHEL images")

        if len(images) == 0:
            raise AbortError("Could not find default Red Hat image")

        image_ids = [
            image.id
            for image in sorted(
                images,
                key=lambda image: datetime.strptime(
                    image.creation_date, "%Y-%m-%dT%H:%M:%S.%f%z"
                ),
                reverse=True,
            )
            if "BETA" not in image.name
        ]

        return image_ids[0]
