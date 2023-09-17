import os
from typing import Optional

from .exceptions import AbortError


class GlobalConfig:
    def __init__(self) -> None:
        self.root_dir = os.path.expanduser("~/.holy")
        self.keys_dir = os.path.join(self.root_dir, "keys")
        self._check_root_dir()

    def _check_root_dir(self):
        if not os.path.isdir(self.root_dir):
            try:
                os.mkdir(self.root_dir)
                os.mkdir(self.keys_dir)
            except:
                raise AbortError(f"Could not create directory: {self.root_dir}")


class Config:
    def __init__(
        self, global_config: GlobalConfig, region: Optional[str], profile: Optional[str]
    ) -> None:
        self.global_config = global_config
        self.aws_region = region
        self.aws_profile = profile
