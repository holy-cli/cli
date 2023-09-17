import logging

import boto3


class ColorPercentStyle(logging.PercentStyle):
    grey = "38"
    green = "32"
    yellow = "33"
    red = "31"

    def _get_color_fmt(self, color_code, bold=False):
        if bold:
            return "\x1b[" + color_code + ";1m" + self._fmt + "\x1b[0m"
        return "\x1b[" + color_code + ";20m" + self._fmt + "\x1b[0m"

    def _get_fmt(self, levelno):
        colors = {
            logging.DEBUG: self._get_color_fmt(self.grey),
            logging.INFO: self._get_color_fmt(self.green),
            logging.WARNING: self._get_color_fmt(self.yellow),
            logging.ERROR: self._get_color_fmt(self.red),
            logging.CRITICAL: self._get_color_fmt(self.red, bold=True),
        }

        return colors.get(levelno, self._get_color_fmt(self.grey))

    def _format(self, record):
        return self._get_fmt(record.levelno) % record.__dict__


class CustomFormatter(logging.Formatter):
    def formatMessage(self, record):
        return ColorPercentStyle(self._fmt).format(record)


def getLogger() -> logging.Logger:
    logger = logging.getLogger("holy-cli")

    if not logger.hasHandlers():
        logger.addHandler(boto3.NullHandler())

    return logger


def setLoggerToStream() -> None:
    logger = getLogger()
    logger.setLevel(logging.DEBUG)

    format_string = "[%(name)s %(levelname)s] %(message)s"
    formatter = CustomFormatter(fmt=format_string)

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    boto3.set_stream_logger("boto3.resources", logging.DEBUG, format_string)
