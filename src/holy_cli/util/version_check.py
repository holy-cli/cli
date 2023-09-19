import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from holy_cli import __version__
from holy_cli.exceptions import AbortError
from holy_cli.log import getLogger

LATEST_RELEASE_API_URL = "https://api.github.com/repos/holy-cli/cli/releases/latest"

log = getLogger()


def version_up_to_date() -> bool:
    tag = _get_latest_tag()
    log.debug(f"Tag name is {tag}")

    return tag == f"v{__version__}"


def _get_latest_tag() -> str:
    request = Request(
        LATEST_RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urlopen(request) as response:
            body = json.loads(response.read())
            return body["tag_name"]
    except HTTPError as err:
        log.error(err)
        raise AbortError("Failed to check for latest version")
