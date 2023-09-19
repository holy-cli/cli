import click
from botocore.exceptions import BotoCoreError, ClientError

from holy_cli import __version__
from holy_cli.log import getLogger

from .global_commands import teardown, update
from .server_commands import server


# Global CLI entry point to catch unhandled botocore exceptions
def entry_point():
    try:
        cli()
    except BotoCoreError as err:
        click.echo(f"Error: {err}", err=True)
        return 1
    except ClientError as err:
        getLogger().error(err.response["Error"])
        click.echo(
            ("Error: {message}").format(message=err.response["Error"]["Message"]),
            err=True,
        )
        return 1


@click.group()
@click.version_option(__version__, prog_name="holy-cli")
def cli() -> None:
    pass


cli.add_command(server)
cli.add_command(teardown)
cli.add_command(update)
