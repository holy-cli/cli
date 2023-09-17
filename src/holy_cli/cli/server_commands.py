import click
from tabulate import tabulate

from holy_cli.cloud.aws import AWS_ARCHITECTURE_VALUES, AWS_OS_USER_MAPPING
from holy_cli.cloud.aws.actions import AWSActions
from holy_cli.cloud.options import CreateServerOptions, ServerDTO
from holy_cli.exceptions import AbortError
from holy_cli.log import setLoggerToStream


@click.group()
def server() -> None:
    """Manage servers"""
    pass


@server.command(name="list")
@click.option(
    "-r",
    "--running",
    help="Only show servers that are running",
    default=False,
    is_flag=True,
    show_default=True,
)
@click.option("--region", help="AWS region to use")
@click.option("--profile", help="AWS profile to use")
@click.option("-v", "--verbose", help="Show verbose output", count=True)
def list_cmd(**kwargs) -> None:
    """List all servers"""
    if kwargs.get("verbose"):
        setLoggerToStream()

    actions = AWSActions.load_from_cli(kwargs.get("region"), kwargs.get("profile"))
    servers = actions.list_servers(kwargs["running"])

    click.echo(tabulate(servers, headers="keys", tablefmt="simple_grid"))


@server.command()
@click.argument("name")
@click.option("--region", help="AWS region to use")
@click.option("--profile", help="AWS profile to use")
@click.option("-v", "--verbose", help="Show verbose output", count=True)
def info(**kwargs) -> None:
    """View info about a server"""
    if kwargs.get("verbose"):
        setLoggerToStream()

    server = ServerDTO(kwargs["name"])
    actions = AWSActions.load_from_cli(kwargs.get("region"), kwargs.get("profile"))
    info = actions.get_server_info(server)
    table = list(map(list, info.items()))

    click.echo(tabulate(table, tablefmt="simple_grid"))


@server.command(short_help="SSH into a server")
@click.argument("name")
@click.option("-u", "--username", help="Username to SSH in with")
@click.option(
    "-s",
    "--save",
    help="Save details to SSH config file (~/.ssh/config)",
    default=False,
    is_flag=True,
    show_default=True,
)
@click.option("--region", help="AWS region to use")
@click.option("--profile", help="AWS profile to use")
@click.option("-v", "--verbose", help="Show verbose output", count=True)
def ssh(**kwargs) -> None:
    """
    SSH into a server. Examples:

    # SSH straight in:

    holy server ssh my_server

    # Save SSH config for use later (VS Code, ssh command etc):

    holy server ssh my_server --save

    # SSH in with a particular username:

    holy server ssh my_server --username=root
    """
    if kwargs.get("verbose"):
        setLoggerToStream()

    server = ServerDTO(kwargs["name"])
    actions = AWSActions.load_from_cli(kwargs.get("region"), kwargs.get("profile"))
    actions.ssh_into_server(server, kwargs.get("username"), kwargs["save"])

    if kwargs["save"]:
        click.echo("SSH details written to ~/.ssh/config")


@server.command()
@click.argument("name")
@click.option("--region", help="AWS region to use")
@click.option("--profile", help="AWS profile to use")
@click.option("-v", "--verbose", help="Show verbose output", count=True)
def start(**kwargs) -> None:
    """Start a server"""
    if kwargs.get("verbose"):
        setLoggerToStream()

    server = ServerDTO(kwargs["name"])
    actions = AWSActions.load_from_cli(kwargs.get("region"), kwargs.get("profile"))
    actions.start_server(server)


@server.command()
@click.argument("name")
@click.option("--region", help="AWS region to use")
@click.option("--profile", help="AWS profile to use")
@click.option("-v", "--verbose", help="Show verbose output", count=True)
def stop(**kwargs) -> None:
    """Stop a server"""
    if kwargs.get("verbose"):
        setLoggerToStream()

    server = ServerDTO(kwargs["name"])
    actions = AWSActions.load_from_cli(kwargs.get("region"), kwargs.get("profile"))
    actions.stop_server(server)


@server.command()
@click.argument("name")
@click.option("--region", help="AWS region to use")
@click.option("--profile", help="AWS profile to use")
@click.option("-v", "--verbose", help="Show verbose output", count=True)
def delete(**kwargs) -> None:
    """Delete a server"""
    if kwargs.get("verbose"):
        setLoggerToStream()

    server = ServerDTO(kwargs["name"])
    actions = AWSActions.load_from_cli(kwargs.get("region"), kwargs.get("profile"))
    actions.delete_server(server)


@server.command(short_help="Manage server ports")
@click.argument("name")
@click.option("--action", help="The action to take (open or close)", required=True)
@click.option("--port", help="The port number", required=True, type=int)
@click.option("--ip", help="IP address to restrict port access to")
@click.option("--region", help="AWS region to use")
@click.option("--profile", help="AWS profile to use")
@click.option("-v", "--verbose", help="Show verbose output", count=True)
def port(**kwargs) -> None:
    """
    Manage inbound server ports. Examples:

    # Open port 80 to the world:

    holy server port my_server --action=open --port=80

    # Close port 80 to the world:

    holy server port my_server --action=close --port=80

    # Open port 80 to a specific IP address:

    holy server port my_server --action=open --port=80 --ip=1.2.3.4
    """
    if kwargs.get("verbose"):
        setLoggerToStream()

    valid_actions = ("open", "close")

    if kwargs["action"] not in valid_actions:
        raise AbortError(
            "Invalid action value, must be one of: " + ", ".join(valid_actions)
        )

    server = ServerDTO(kwargs["name"])
    actions = AWSActions.load_from_cli(kwargs.get("region"), kwargs.get("profile"))
    actions.change_port(server, kwargs["port"], kwargs["action"], kwargs.get("ip"))

    click.echo(
        f"Port {kwargs['port']} has been {'opened' if kwargs['action'] == 'open' else 'closed'} to {kwargs.get('ip') or 'the world'}"
    )


@server.command(short_help="Create a new server")
@click.argument("name", required=False)
@click.option(
    "--os",
    help="Operating system: " + ", ".join(AWS_OS_USER_MAPPING.keys()),
    default="amazon-linux",
    show_default=True,
)
@click.option(
    "--architecture",
    help="CPU architecture: " + ", ".join(AWS_ARCHITECTURE_VALUES),
    default="x86_64",
    show_default=True,
)
@click.option(
    "--image-id",
    help="Amazon machine image ID to use (overrides OS and architecture options)",
)
@click.option(
    "--type",
    help="Instance type to use",
    default="t2.micro",
    show_default=True,
    required=True,
)
@click.option(
    "--disk-size",
    help="Disk size in GB",
    type=int,
    default=8,
    show_default=True,
    required=True,
)
@click.option(
    "--ports",
    help="Port numbers to open (comma seperated list)",
    default="22,80,443",
    show_default=True,
)
@click.option(
    "--actions",
    help="Allowed actions the server can make when calling other AWS services (comma seperated list e.g. s3:*,logs:GetLogEvents)",
)
@click.option(
    "--script",
    help="Path to a script file to run on the server upon creation",
    type=click.Path(exists=True),
)
@click.option(
    "--iam-profile",
    help="IAM instance profile name or ARN to use (overrides actions option)",
)
@click.option(
    "--subnet-id",
    help="A specific subnet ID to launch in",
)
@click.option("--region", help="AWS region to use")
@click.option("--profile", help="AWS profile to use")
@click.option("-v", "--verbose", help="Show verbose output", count=True)
def create(**kwargs) -> None:
    """
    Create a new server. Examples:

    # No options, create with a random name using amazon-linux OS on a micro instance (within the free tier):

    holy server create

    # Create with a specific name, using ubuntu on a large compute optimized instance with 30GB disk space:

    holy server create my_server --os=ubuntu:22 --type=c4.large --disk-size=30

    # Create with a specific Amazon machine image:

    holy server create my_server --image-id="ami-00d5053dee71cee04"

    # Create and open ports 22 and 3000 to the world:

    holy server create my_server --ports="22,3000"

    # Create and allow the server to list all S3 buckets:

    holy server create my_server --actions="s3:ListAllMyBuckets"

    # Create and run a script once launched:

    holy server create my_server --script=/path/to/install_software.sh
    """
    if kwargs.get("verbose"):
        setLoggerToStream()

    options = CreateServerOptions.load_from_cli(**kwargs)
    actions = AWSActions.load_from_cli(kwargs.get("region"), kwargs.get("profile"))
    instance = actions.create_server(options)
    ssh_cmd = f"holy server ssh {options.name}"

    if kwargs.get("region"):
        ssh_cmd += f" --region={kwargs['region']}"

    if kwargs.get("profile"):
        ssh_cmd += f" --profile={kwargs['profile']}"

    click.echo(
        f"Your server is ready:\n\nIP: {instance.public_ip_address}\nDNS: {instance.public_dns_name}\n\nTo connect run: {ssh_cmd}"
    )
