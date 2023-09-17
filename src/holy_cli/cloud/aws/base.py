from typing import List, Optional, Sequence

from boto3 import Session
from mypy_boto3_ec2 import EC2ServiceResource
from mypy_boto3_ec2.literals import ResourceTypeType
from mypy_boto3_ec2.type_defs import TagSpecificationTypeDef, TagTypeDef

from holy_cli.config import Config
from holy_cli.log import getLogger

from . import AWS_OS_USER_MAPPING, AWS_TAG_KEY, AWS_TAG_VALUE


class BaseWrapper:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.log = getLogger()
        self.ec2 = self.init_ec2()

    def init_ec2(self) -> EC2ServiceResource:
        session = self.init_boto3_session()
        return session.resource("ec2")

    def init_boto3_session(self) -> Session:
        return Session(
            region_name=self.config.aws_region, profile_name=self.config.aws_profile
        )

    def get_tags_for_resource(
        self,
        resource_type: ResourceTypeType,
        resource_name: Optional[str] = None,
        additional_tags: Optional[dict] = None,
    ) -> Sequence[TagSpecificationTypeDef]:
        return [
            {
                "ResourceType": resource_type,
                "Tags": self.get_tags(resource_name, additional_tags),
            }
        ]

    def get_tags(
        self,
        resource_name: Optional[str] = None,
        additional_tags: Optional[dict] = None,
    ) -> Sequence[TagTypeDef]:
        tags: Sequence[TagTypeDef] = [{"Key": AWS_TAG_KEY, "Value": AWS_TAG_VALUE}]

        if resource_name is not None:
            name_tag: TagTypeDef = {"Key": "Name", "Value": resource_name}
            tags.append(name_tag)

        if additional_tags is not None:
            for key in additional_tags.keys():
                additional: TagTypeDef = {
                    "Key": key,
                    "Value": additional_tags[key],
                }
                tags.append(additional)

        return tags

    def get_tag_value(self, tags: List[TagTypeDef], tag_key: str) -> Optional[str]:
        tags = list(tags)
        return next((tag["Value"] for tag in tags if tag["Key"] == tag_key), None)
