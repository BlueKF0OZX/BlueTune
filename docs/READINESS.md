# BlueTune readiness — 2026-09-14

**Suitable for a supervised early trial on ASL3 with supported SimpleUSB
statistics. Not a certification of radio audio quality or every ASL3 system.**

## Verified

- 26 backend tests on Windows and Debian 12 / Python 3.11 in an isolated ASL3 lab.
- Demo/import browser flows, exports, comparisons, narrow screen layouts,
  simulated live failures and cancellation. The GitHub workflow also runs the
  browser suite with Chromium.
- Real SimpleUSB voice statistics collected over SSH and analyzed through the
  import path. No overload was detected in that sample; no listening judgment
  was made from the numbers.
- Real live web collection through an SSH tunnel, from a normal user account
  using existing noninteractive sudo permission. Quiet input stayed
  inconclusive without speech confirmation, and cancellation discarded data.
- A clean private ASL3 snapshot cloned for this trial, with a newly created
  unprivileged account and a fresh copy of BlueTune. Demo startup succeeded.
  Missing access and missing SimpleUSB hardware produced explained failures.
- The documented three-command sudo policy passed `visudo` validation and
  actual sudo authorization checks. All three reads were allowed; a shell,
  Python, keying, gain changes, interface selection, and the interactive
  statistics command were denied. Revoking the policy revoked access.
- Request admission is bounded at eight clients. Slow connections cannot grow
  an unlimited request-thread pool, and the server recovers after they close.
  Concurrent Asterisk readings are rejected rather than queued. Disconnected
  clients and unsupported statistics do not become successful measurements.
- Every new live sample clears the prior speech confirmation. Older in-flight
  confirmation responses cannot overwrite a newer checkbox choice.

The clean lab had no radio hardware. It verifies setup, permission enforcement,
and failure behavior; physical-node evidence comes from the separate live trial.
No fresh operating system was installed from an ISO during this test: the lab
started from a clean ASL3 snapshot predating BlueNode and BlueTune installation.

## Still requires operator/hardware evidence

1. Run the live collection button while speaking, then compare with the ASL3
   tuning display and a consenting listener. The earlier voice trial used import.
2. Repeat on another operator's hardware and supported ASL3 version.
3. Test real USB loss/reconnection on an isolated physical node. Current missing
   interface tests do not establish every driver's behavior during unplugging.
4. Observe longer normal use on constrained Pi hardware. No overnight endurance
   pass or RF deviation calibration is claimed.

## Known design limits

ASL's rolling statistics have no upstream sample timestamp. Successful command
execution proves the response arrived, not that new audio frames were processed.
Repeated identical numbers are not enough to prove a stalled stream. Device
selection is global in the upstream CLI; before/after name checks do not detect
every possible change away and back, so close other tuning tools during a test.

Software measurements cannot replace transmitter deviation equipment, identify
voice versus noise/transients, or certify intelligibility. USBRadio, automatic
tuning, audio playback, public web hosting, and restoration of configuration
backups are outside this preview.
