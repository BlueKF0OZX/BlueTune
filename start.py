"""First-user launcher. No packages, service installation, or permission changes."""
import argparse
import os
from pathlib import Path
import sys


def prepare_live(device=None, factory=None):
    from collector import Collector
    factory = factory or Collector
    errors = []
    for sudo in (False, True):
        try:
            probe = factory(device=device or "probe", use_sudo=sudo)
            active = probe.device_from(probe.command("susb active"))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        # Once access works, a mismatched device or invalid sample is not an access problem.
        if device and active != device:
            raise ValueError(f"Expected device {device}, but ASL3 has {active} selected. Select the intended interface in ASL3 and retry.")
        collector = factory(device=active, use_sudo=sudo)
        collector.sample()
        return collector
    raise ValueError("Live check could not finish. Direct access: " + errors[0] + "\nExisting sudo access: " + errors[-1])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start a BlueTune checkup without changing your node settings.")
    parser.add_argument("--live", action="store_true", help="Check the active SimpleUSB device and open live mode")
    parser.add_argument("--check", action="store_true", help="Check prerequisites and live access, then exit")
    parser.add_argument("--device", help="Require this exact SimpleUSB device")
    parser.add_argument("--port", type=int, default=8091)
    args = parser.parse_args(argv)
    try:
        if sys.version_info < (3, 11):
            raise ValueError("BlueTune needs Python 3.11 or newer. On ASL3, check your supported Debian/Python installation.")
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            raise ValueError("Run this command as your normal login account, without sudo.")
        root = Path(__file__).resolve().parent
        for name in ("analysis.py", "collector.py", "app.py", "web/index.html", "web/app.js", "web/style.css"):
            if not (root / name).is_file():
                raise ValueError(f"The download is incomplete: {name} is missing. Download or clone the complete BlueTune repository.")
        if not 1 <= args.port <= 65535:
            raise ValueError("Choose a port between 1 and 65535.")
        print("PASS: Python and all application files are available.")
        collector = None
        if args.live or args.check:
            if sys.platform != "linux":
                raise ValueError("Live collection runs on the ASL3 Linux node. On this computer, use python start.py for demo/import mode.")
            collector = prepare_live(args.device)
            print(f"PASS: SimpleUSB device {collector.device} returned readable receive statistics.")
            print("Access: " + ("existing noninteractive sudo permission" if collector.use_sudo else "existing Asterisk socket permission"))
            print("No tuning settings or permissions were changed. Quiet readings are normal before speaking.")
        if args.check:
            return 0
        from app import serve
        serve(args.port, collector)
        return 0
    except (ValueError, OSError) as exc:
        print("\nBlueTune could not start: " + str(exc), file=sys.stderr)
        print("Help: docs/FIRST_CHECKUP.md. If the address is in use, retry with --port 8092.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
