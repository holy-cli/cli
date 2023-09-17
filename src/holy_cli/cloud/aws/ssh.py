import os
import platform
import subprocess
import sys
from typing import Optional

from mypy_boto3_ec2.service_resource import Instance

from holy_cli.exceptions import AbortError

from .base import AWS_OS_USER_MAPPING, BaseWrapper


class SSHWrapper(BaseWrapper):
    def ssh_into_instance(
        self, instance: Instance, key_file_path: str, username: Optional[str]
    ) -> None:
        if instance.state["Name"] != "running":
            raise AbortError("Server is not running")

        if not os.path.exists(key_file_path):
            raise AbortError(
                f"Key file is missing, you may need to re-create the server"
            )

        user = username or self._get_instance_username(instance)
        host = instance.public_ip_address

        try:
            result = self._run_ssh_cmd(key_file_path, user, host)
        except FileNotFoundError:
            raise AbortError(
                f"Could not find SSH tool, please try run manually:\n\n/path/to/ssh -i {key_file_path} {user}@{host}"
            )

        if result.returncode:
            err = result.stderr.decode("utf-8")
            self.log.error(f"SSH error response: {err}")
            debug_cmd = f"ssh -v -i {key_file_path} {user}@{host}"

            if "Permission denied" in err:
                raise AbortError(
                    f"Could not SSH into server (permission denied), to debug run:\n\n{debug_cmd}\n\nNote: In some cases the username may not be correct, check your AMI usage instructions and pass in with the --username flag"
                )

            if "Could not resolve" in err:
                raise AbortError(
                    f"Could not SSH into server (hostname could not be resolved), to debug run:\n\n{debug_cmd}"
                )

            if "Connection refused" in err:
                raise AbortError(
                    f"Could not SSH into server (connection refused), if the server has just started try again in a minute or to debug run:\n\n{debug_cmd}"
                )

    def save_to_file(
        self, instance: Instance, key_file_path: str, username: Optional[str]
    ) -> None:
        if instance.state["Name"] != "running":
            raise AbortError("Server is not running")

        if not os.path.exists(key_file_path):
            raise AbortError(
                f"Key file is missing, you may need to re-create the server"
            )

        user = username or self._get_instance_username(instance)
        host = instance.public_ip_address
        name = self.get_tag_value(instance.tags, "Name")
        ssh_config_file_path = os.path.expanduser("~/.ssh/config")
        ssh_contents = f"\nHost {name}\n\tUser {user}\n\tHostName {host}\n\tIdentityFile {key_file_path}"

        with open(ssh_config_file_path, "a") as f:
            f.write(ssh_contents)

    def _get_instance_username(self, instance: Instance) -> str:
        os = self.get_tag_value(instance.tags, "holy-cli:os")
        user = "ec2-user"

        if os is None:
            self.log.warning("Could not find OS for instance")
        else:
            if os in AWS_OS_USER_MAPPING:
                user = AWS_OS_USER_MAPPING[os]
            else:
                self.log.warning("Could not find OS in username mapping")

        return user

    def _run_ssh_cmd(
        self, key_path: str, user: str, host: str
    ) -> subprocess.CompletedProcess:
        cmd = [
            self._get_ssh_path(),
            "-i",
            key_path,
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "LogLevel=ERROR",
            f"{user}@{host}",
        ]

        self.log.debug(f"Trying SSH command: {' '.join(cmd)}")
        return subprocess.run(cmd, stderr=subprocess.PIPE)

    def _get_ssh_path(self) -> str:
        if sys.platform == "win32":
            system32 = os.path.join(
                os.environ["SystemRoot"],
                "SysNative" if platform.architecture()[0] == "32bit" else "System32",
            )
            ssh_path = os.path.join(system32, "OpenSSH\\ssh.exe")

            if not os.path.exists(ssh_path):
                ssh_path = os.path.join(os.environ["ProgramFiles"], "OpenSSH\\ssh.exe")

            if not os.path.exists(ssh_path) and os.environ.get("ProgramFiles(x86)"):
                ssh_path = os.path.join(
                    os.environ["ProgramFiles(x86)"], "OpenSSH\\ssh.exe"
                )

            return ssh_path
        else:
            if "SSH_AUTH_SOCK" not in os.environ:
                raise AbortError(
                    "SSH agent is not running, please try running: eval $(ssh-agent -s)"
                )

            return "ssh"
