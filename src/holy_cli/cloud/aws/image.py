from datetime import datetime
from typing import Optional

from mypy_boto3_ec2.service_resource import Image
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

    def find_image_choices(self, os: str, architecture: str) -> Image:
        if os == "amazon-linux":
            return self._find_amazon_linux_image(architecture)

        if os.startswith("ubuntu"):
            return self._find_ubuntu_image(os, architecture)

        if os.startswith("rhel"):
            return self._find_redhat_image(os, architecture)

        raise AbortError("OS not recognised")

    def get_image_by_id(self, image_id: str) -> Optional[Image]:
        results = list(self.ec2.images.filter(ImageIds=[image_id]))

        if len(results) > 0:
            return results[0]

    def _find_amazon_linux_image(self, architecture: str) -> Image:
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

        return image

    def _find_ubuntu_image(self, os: str, architecture: str) -> Image:
        if architecture == "x86_64":
            architecture = "amd64"

        version = os.split(":")[1]
        version = f"{version}.04"  # todo: update when minor version changes

        param_name = f"/aws/service/canonical/ubuntu/server/{version}/stable/current/{architecture}/hvm/ebs-gp2/ami-id"
        self.log.debug(f"Looking up SSM param name {param_name}")

        try:
            result = self.ssm.get_parameter(Name=param_name)
        except:
            raise AbortError("Could not find default Ubuntu image")

        image = self.get_image_by_id(result["Parameter"]["Value"])

        if image is None:
            raise AbortError("Could not find default Ubuntu image")

        self.log.debug(f"Chose {image.name} - {image.description}")

        return image

    def _find_redhat_image(self, os: str, architecture: str) -> Image:
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

        images = [
            image
            for image in sorted(
                images,
                key=lambda image: datetime.strptime(
                    image.creation_date, "%Y-%m-%dT%H:%M:%S.%f%z"
                ),
                reverse=True,
            )
            if "BETA" not in image.name
        ]

        if len(images) == 0:
            raise AbortError("Could not find default Red Hat image")

        image = images[0]
        self.log.debug(f"Chose {image.name} - {image.description}")

        return image
