"""Explicit, read-only SimpleUSB CLI adapter. Never accepts a browser command."""
import re
import subprocess
import threading
from analysis import parse_stats

ALLOWED = frozenset(("susb active", "susb show settings", "susb tune menu-support Y"))


class Collector:
    def __init__(self, executable="/usr/sbin/asterisk", device=None, runner=subprocess.run, use_sudo=False):
        self.executable, self.device, self.runner = executable, device, runner
        self.lock = threading.Lock()
        self.use_sudo = use_sudo
        if not device or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", device):
            raise ValueError("Live mode requires the expected SimpleUSB device name (--device).")

    def command(self, command):
        if command not in ALLOWED:
            raise ValueError("Command is not permitted.")
        try:
            args = (["/usr/bin/sudo", "-n", "--"] if self.use_sudo else []) + [self.executable, "-rx", command]
            result = self.runner(args, capture_output=True, text=True,
                                 timeout=3, check=False, encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("Cannot read Asterisk. Check that it is running and this account can access its control socket.") from exc
        if result.returncode:
            raise ValueError("Asterisk access was denied or its control socket is unavailable. Check that Asterisk is running. See docs/FIRST_CHECKUP.md for the limited-access setup; do not run BlueTune with sudo.")
        if len(result.stdout) > 65536:
            raise ValueError("Asterisk returned an unexpectedly large response.")
        return result.stdout

    @staticmethod
    def device_from(output):
        match = re.search(r"Active Simple USB Radio device is \[([A-Za-z0-9_-]{1,64})\]\.", output)
        if not match:
            raise ValueError("No supported active SimpleUSB interface was reported. Check ASL3's interface selection. USBRadio and radio-less nodes are not supported for live collection.")
        return match[1]

    def active(self):
        output = self.command("susb active")
        if self.device_from(output) != self.device:
            raise ValueError("The active SimpleUSB device does not match this session. Select the intended device in ASL3, then retry. USBRadio is not supported in this first version.")

    def sample(self):
        with self.lock:
            self.active()
            raw = self.command("susb tune menu-support Y")
            samples = parse_stats(raw)
            self.active()
            return samples[-1]

    def settings(self):
        with self.lock:
            self.active()
            raw = self.command("susb show settings")
            self.active()
            return raw
