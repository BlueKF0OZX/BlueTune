# Your first BlueTune checkup

BlueTune is an early preview for **ASL3 with SimpleUSB**. Demo and pasted-sample
mode also work on ordinary computers. USBRadio live collection is not supported.

## 1. Download on your ASL3 node

Sign in to your node as your usual account. Keep automatic radio/network
behavior as configured; BlueTune does not alter it.

```sh
git clone https://github.com/BlueKF0OZX/BlueTune.git
cd BlueTune
bash start.sh --check
```

If `git` is missing, install it through your usual Debian package manager
(`sudo apt-get install git`). ASL3 must provide Python 3.11 or newer.
Use a new folder for this first evaluation. Existing users can update a clean
checkout with `git pull --ff-only` before running the check.

The check reports the active SimpleUSB device and verifies that it returns
receive statistics. It first tries direct Asterisk access and then your account's
existing noninteractive sudo access. It never changes permissions automatically.
For a multi-node installation, require the device you intend to measure:

```sh
bash start.sh --check --device 1999
```

Replace `1999` with your actual device name. An incorrect device stops the check.
Do not use another tuning session at the same time.

## 2. Open BlueTune

On the node, run:

```sh
bash start.sh --live
```

Leave that terminal open. On your own computer, open a **second terminal** and
create a tunnel, replacing the example with the same login/address you normally
use for your node:

```sh
ssh -N -L 8091:127.0.0.1:8091 your-login@your-node-address
```

Leave this second terminal open too. On that computer open
**http://127.0.0.1:8091** in your browser. This is a local SSH tunnel; no router
port-forwarding is needed. If you run a browser directly on the node, no tunnel
is needed. Phone-sized layouts are supported, but phone tunnel setup is outside
this first-user path.

If port 8091 is already in use on your computer, change the first port in the
tunnel to `8092` and open http://127.0.0.1:8092. If the node's port is in use,
start with `--port 8092` and use `8092` for both tunnel ports.

To try the interface without connecting to a node, run `python3 start.py` on
Linux or `python start.py` on Windows. Demo readings are synthetic.

## 3. Take a sample

1. Confirm that BlueTune shows the expected SimpleUSB device and live source.
2. Use an appropriate test frequency and a consenting peer if your node is linked.
3. Click **Measure for 10 seconds**, then speak normally into your radio. Keep
   microphone distance consistent and include your usual louder voice peaks.
4. Check **I spoke into the node receiver during this sample**. BlueTune does
   not identify speech automatically.
5. Read the result and **Save as baseline**, then **Export checkup** to keep it.
   Page memory is lost on refresh or closing the tab.
6. Ask a consenting operator about clarity, noise, and loudness. A numerical
   no-overload result does not certify how your audio sounds.

Before making a manual adjustment, use ASL3's **Backup and Restore** menu.
Change only one setting at a time in ASL3, then repeat under the same conditions.
BlueTune's settings snapshot is a reference, not a restorable backup.

## If access fails

- **Asterisk unavailable:** check that ASL3/Asterisk is running normally. Do not
  restart your radio system just to satisfy BlueTune without investigating.
- **Unsupported interface:** live mode requires SimpleUSB with the uppercase
  one-shot `Y` statistics command. Use demo/import mode if your version or driver
  does not provide it.
- **Wrong device:** select the intended interface through ASL3's tuning menu,
  close the menu, and repeat `--check --device YOUR_DEVICE`.
- **Permission denied:** don't run the web app as root and don't grant blanket
  passwordless sudo access just for BlueTune. An administrator can optionally
  authorize only the following commands with `sudo visudo -f /etc/sudoers.d/bluetune`.
  Replace `YOUR_LOGIN` with the real Linux account, and confirm the Asterisk
  binary is the root-owned `/usr/sbin/asterisk` on this installation:

```sudoers
YOUR_LOGIN ALL=(root) NOPASSWD: /usr/sbin/asterisk -rx susb active
YOUR_LOGIN ALL=(root) NOPASSWD: /usr/sbin/asterisk -rx susb tune menu-support Y
YOUR_LOGIN ALL=(root) NOPASSWD: /usr/sbin/asterisk -rx susb show settings
```

No wildcards or general `asterisk`, shell, Python, or editor permissions are
needed. The launcher always supplies fixed argument lists and `sudo -n`.
This optional policy must be reviewed/validated with `visudo` on the intended
machine; it is not automatically installed or tested on every ASL3 image.

## Stop and remove

Press Ctrl+C in the BlueTune terminal and the tunnel terminal. There is no
installed service to disable. Keep exported reports elsewhere if wanted, then
remove your downloaded BlueTune folder. If an administrator created the optional
sudoers file specifically for this trial, have them remove that file as well.
Do not remove any pre-existing ASL3 permissions.

## Tell us what happened

Use [the bug report form](https://github.com/BlueKF0OZX/BlueTune/issues/new?template=bug_report.md).
Include `git rev-parse HEAD`, ASL3/Asterisk and Python versions, radio interface,
browser, steps taken, and the exact error or result. Review exports for personal
labels before sharing. Never post passwords, SSH keys, or full node configuration.
