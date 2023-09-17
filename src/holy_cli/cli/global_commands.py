import click

from holy_cli.cloud.aws.actions import AWSActions
from holy_cli.log import setLoggerToStream


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
