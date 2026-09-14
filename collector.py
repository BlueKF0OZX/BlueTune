"""Explicit, read-only SimpleUSB CLI adapter. Never accepts a browser command."""
import re
import subprocess
import threading
from analysis import parse_stats

ALLOWED = frozenset(("susb active", "susb show settings", "susb tune menu-support Y"))


class Collector:
    def __init__(self, executable="/usr/sbin/asterisk", device=None, runner=subprocess.run):
        self.executable, self.device, self.runner = executable, device, runner
        self.lock = threading.Lock()
        if not device or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", device):
            raise ValueError("Live mode requires the expected SimpleUSB device name (--device).")

    def command(self, command):
        if command not in ALLOWED:
            raise ValueError("Command is not permitted.")
        try:
            result = self.runner([self.executable, "-rx", command], capture_output=True, text=True,
                                 timeout=3, check=False, encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError("Cannot read Asterisk. Check that it is running and this account can access its control socket.") from exc
        if result.returncode or len(result.stdout) > 65536:
            raise ValueError("Asterisk did not return a usable response.")
        return result.stdout

    def active(self):
        output = self.command("susb active")
        match = re.search(r"Active Simple USB Radio device is \[([A-Za-z0-9_-]{1,64})\]\.", output)
        if not match or match[1] != self.device:
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
