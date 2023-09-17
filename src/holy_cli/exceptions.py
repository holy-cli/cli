from click import ClickException


class AbortError(ClickException):
    """There was an exception that requires the program to abort (will return an exit code of 1)"""
