from typing import Optional

from mypy_boto3_ec2.service_resource import Subnet, Vpc

from .base import AWS_TAG_KEY, AWS_TAG_VALUE, BaseWrapper


class VPCWrapper(BaseWrapper):
    """Encapsulates Amazon EC2 VPC actions."""

    def teardown(self) -> None:
        vpc = self.get_vpc()

        if vpc is None:
            return

        for subnet in list(vpc.subnets.all()):
            self.log.debug(f"Deleting subnet {subnet.id}")
            subnet.delete()

        for ig in list(vpc.internet_gateways.all()):
            self.log.debug(f"Deleting internet gateway {ig.id}")
            ig.detach_from_vpc(VpcId=vpc.id)
            ig.delete()

        self.log.debug(f"Deleting VPC {vpc.id}")
        vpc.delete()

    def get_vpc(self) -> Optional[Vpc]:
        results = list(
            self.ec2.vpcs.filter(
                Filters=[{"Name": f"tag:{AWS_TAG_KEY}", "Values": [AWS_TAG_VALUE]}]
            )
        )

        if len(results) > 0:
            return results[0]

    def get_subnet(self, subnet_id: str) -> Optional[Subnet]:
        results = list(self.ec2.subnets.filter(SubnetIds=[subnet_id]))

        if len(results) > 0:
            return results[0]

    def create(self) -> Vpc:
        vpc_cidr_block = "10.0.0.0/16"

        # Create VPC
        vpc = self.ec2.create_vpc(
            CidrBlock=vpc_cidr_block,
            TagSpecifications=self.get_tags_for_resource("vpc", "holy-vpc"),
        )
        self.log.debug(f"VPC {vpc.id} created")

        # Create Internet Gateway
        igw = self.ec2.create_internet_gateway(
            TagSpecifications=self.get_tags_for_resource(
                "internet-gateway", "holy-internet-gateway"
            ),
        )
        self.log.debug(f"Internet Gateway {igw.id} created")

        # Attach Internet Gateway to VPC
        vpc.attach_internet_gateway(InternetGatewayId=igw.id)
        self.log.debug("Internet Gateway attached to VPC")

        # Modify VPC to enable DNS hostnames
        vpc.modify_attribute(EnableDnsHostnames={"Value": True})
        self.log.debug("Enabled DNS hostnames on VPC")

        # Create Public Subnet
        subnet = vpc.create_subnet(
            CidrBlock=vpc_cidr_block,
            TagSpecifications=self.get_tags_for_resource("subnet", "holy-subnet"),
        )
        self.log.debug(f"Public Subnet {subnet.id} created")

        # Add route to Internet Gateway
        route_tables = list(vpc.route_tables.all())
        route_tables[0].create_route(DestinationCidrBlock="0.0.0.0/0", GatewayId=igw.id)
        self.log.debug("Added route to Internet Gateway")

        # Modify Subnet to enable auto-assign public IPv4 addresses
        # https://github.com/boto/boto3/issues/276
        subnet.meta.client.modify_subnet_attribute(SubnetId=subnet.id, MapPublicIpOnLaunch={"Value": True})  # type: ignore
        self.log.debug("Public IP auto-assign enabled for Subnet")

        return vpc
