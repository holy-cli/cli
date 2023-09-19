import click

from holy_cli.cloud.aws.actions import AWSActions
from holy_cli.log import setLoggerToStream
from holy_cli.util import version_up_to_date


@click.command()
@click.option("--region", help="AWS region to use")
@click.option("--profile", help="AWS profile to use")
@click.option("-v", "--verbose", help="Show verbose output", count=True)
def teardown(**kwargs) -> None:
    """Remove all holy infrastructure"""
    if kwargs.get("verbose"):
        setLoggerToStream()

    click.confirm(
        "Are you sure you want to remove all holy infrastructure?", abort=True
    )

    actions = AWSActions.load_from_cli(kwargs.get("region"), kwargs.get("profile"))
    actions.teardown()

    click.echo("All holy infrastructure removed")


@click.command()
@click.option("-v", "--verbose", help="Show verbose output", count=True)
def update(**kwargs) -> None:
    """Check for the latest version"""
    if kwargs.get("verbose"):
        setLoggerToStream()

    if version_up_to_date():
        click.echo("Version is up to date")
    else:
        click.echo(
            "A new version is available, please run: pip install --upgrade holy-cli"
        )
