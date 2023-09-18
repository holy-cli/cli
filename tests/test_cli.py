from click.testing import CliRunner

from holy_cli import __version__
from holy_cli.cli import cli


def test_version_cmd():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert result.output == f"holy-cli, version {__version__}\n"


def test_server_cmd():
    runner = CliRunner()
    result = runner.invoke(cli, ["server"])
    assert result.exit_code == 0
