"""Conservative interpretation of ASL receive statistics; no audio or radio controls."""
import math
import re

NUMBER = r"-?\d+(?:\.\d+)?"
ROW = re.compile(rf"RxAudioStats:\s+Pk\s+({NUMBER})\s+Avg Pwr\s+({NUMBER})\s+Min\s+({NUMBER})\s+Max\s+({NUMBER})\s+dBFS\s+ClipCnt\s+(\d+)")


def parse_stats(text):
    if not isinstance(text, str) or len(text) > 65536:
        raise ValueError("Paste up to 64 KB of receive statistics.")
    lines = [line.strip() for line in text.splitlines() if "RxAudioStats:" in line]
    if not lines or len(lines) > 120:
        raise ValueError("Expected 1–120 complete RxAudioStats lines from ASL3.")
    samples = []
    for line in lines:
        match = ROW.fullmatch(line)
        if not match:
            raise ValueError("A receive-statistics line is incomplete or unsupported. Collect a fresh sample.")
        peak, average, minimum, maximum = map(float, match.groups()[:4])
        clips = int(match[5])
        if any(not math.isfinite(x) or not -96 <= x <= 0 for x in (peak, average, minimum, maximum)):
            raise ValueError("Audio levels must be finite values between -96 and 0 dBFS.")
        # ASL rounds power to whole dB and peak to tenths; permit rounding differences.
        if not minimum <= average <= maximum or maximum > peak + 1 or clips > 100000000:
            raise ValueError("The receive statistics are inconsistent. Collect a fresh sample.")
        samples.append(dict(peak=peak, average=average, minimum=minimum, maximum=maximum, clips=clips))
    return samples


def assess(samples, speech_confirmed=False):
    peak = max(s["peak"] for s in samples)
    power = max(s["average"] for s in samples)
    clips = max(s["clips"] for s in samples)
    if not speech_confirmed:
        status, title, advice = "unknown", "Confirm your speech sample", "These readings alone cannot identify your voice. Confirm that you spoke normally into the node receiver during this sample before using tuning advice."
    elif clips:
        status, title, advice = "warning", "Clipping appeared in this sample", "Reduce the receive level slightly using ASL3’s tuning menu, then repeat with the same radio, distance, and speaking volume. BlueTune does not change settings."
    elif peak > -3 or power > -12:
        status, title, advice = "warning", "Leave more room for voice peaks", "This sample exceeded ASL3’s receive-level guidance. Reduce the receive level slightly and repeat at normal to loud speaking volume."
    elif peak < -40:
        status, title, advice = "unknown", "Very little input was measured", "Check that the receiver heard your transmission and that the correct interface was selected. Repeat before increasing gain; silence is not evidence of a tuning fault."
    else:
        status, title, advice = "good", "No overload detected in this sample", "These readings stayed below the overload thresholds. Listen with a consenting test peer to judge loudness, noise, and clarity; these numbers do not certify audio quality."
    return dict(status=status, title=title, advice=advice, peak=peak, max_average=power,
                max_clip_count=clips, sample_count=len(samples), speech_confirmed=speech_confirmed,
                note="ASL statistics use rolling windows. ClipCnt is the largest observed window count, not a sum or a count of transmissions.")
