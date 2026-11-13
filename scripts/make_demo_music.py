"""Add a synthesized background track to the demo video -> docs/demo/pipeline_demo_music.mp4.

The music is generated here from sine waves (no samples, no downloads, so no licence to
clear): a slow warm pad, a soft mallet-like pulse and a quiet bass, in D major. It is
scored to the picture: the chord changes on every animation beat, read from the BEATS
table in pipeline_demo.html. Beat lengths are whole seconds and the pulse plays every
half second, so each on-screen change lands exactly on a note.

Run: conda run -n xai python scripts/make_demo_music.py     (after scripts/record_demo.py)
"""
from __future__ import annotations
import re, subprocess, tempfile, wave
from pathlib import Path
import numpy as np
from scipy.signal import fftconvolve

DEMO = Path(__file__).resolve().parents[1] / "docs" / "demo"
SILENT, OUT = DEMO / "pipeline_demo.mp4", DEMO / "pipeline_demo_music.mp4"
SR, STEP = 44100, .5
# (bass note, pad voices) as MIDI numbers: Dmaj9, Bm11, Gmaj9, A6/9
CHORDS = [(38, [50, 57, 61, 64, 66]), (35, [47, 54, 57, 62, 64]),
          (43, [55, 59, 62, 66, 69]), (45, [57, 61, 64, 66, 71])]
ORDER = [0, 2, 1, 3, 2, 4, 1, 3]              # which chord tone each pulse note plays
VEL = [1, .5, .7, .45, .85, .5, .65, .45]     # and how hard; the first lands on the chord change
ANSWERS = 6                                    # rail stage where the pulse gains an upper octave
TAU = 2 * np.pi
hz = lambda midi: 440 * 2 ** ((midi - 69) / 12)
clock = lambda seconds: np.arange(int(seconds * SR)) / SR


def pad(midi: int, dur: float) -> np.ndarray:
    """Three slightly detuned sines plus two soft overtones, swelling in and out."""
    t, f = clock(dur + 3), hz(midi)
    s = sum(np.sin(TAU * f * (1 + d) * t + ph) for d, ph in ((-.003, 0), (0, 1), (.003, 2))) / 3
    s += .25 * np.sin(TAU * 2 * f * t) + .08 * np.sin(TAU * 3 * f * t)
    return s * np.minimum(1, t / 1.5) * np.minimum(1, (t[-1] - t) / 3)


def pluck(midi: int) -> np.ndarray:
    """Mallet-like note: overtones die away faster than the fundamental."""
    t, f = clock(2.5), hz(midi)
    s = (np.sin(TAU * f * t) * np.exp(-t / .7) + .3 * np.sin(TAU * 2 * f * t) * np.exp(-t / .3)
         + .12 * np.sin(TAU * 4 * f * t) * np.exp(-t / .1))
    return s * np.minimum(1, t / .004)


def bass(midi: int, dur: float) -> np.ndarray:
    t, f = clock(dur + 1), hz(midi)
    return (np.sin(TAU * f * t) + .3 * np.sin(TAU * 2 * f * t)) * np.minimum(1, t / .3) * np.minimum(1, t[-1] - t)


def compose(beats: list[tuple[int, int]]) -> np.ndarray:
    total = sum(d for d, _ in beats)
    mix = np.zeros((int((total + 6) * SR), 2))

    def put(sig, at, gain, pan=.5):  # pan 0 = left, 1 = right
        i = int(round(at * SR))
        mix[i:i + len(sig)] += gain * sig[:, None] * [np.cos(pan * np.pi / 2), np.sin(pan * np.pi / 2)]

    start, last = 0, len(beats) - 1
    first_pulse = next(sum(d for d, _ in beats[:i]) for i, (_, stage) in enumerate(beats) if stage >= 0)
    for b, (dur, stage) in enumerate(beats):
        # end on A -> D so the last picture arrives with a resolution
        root, voices = CHORDS[0 if b == last else 3 if b == last - 1 else b % 4]
        put(bass(root, dur), start, .2)
        for v, pan in zip(voices, np.linspace(.2, .8, len(voices))):
            put(pad(v, dur), start, .1, pan)
        if b == last:  # no pulse under the closing frame, just one rolled chord
            for i, v in enumerate(voices[::2]):
                put(pluck(v + 12), start + i * .15, .16, .3 + .2 * i)
        elif stage >= 0:  # the opening two beats (the bare alert) stay pad-only
            for k in range(int(dur / STEP)):
                at, pan = start + k * STEP, .35 + .3 * (k % 2)
                note = pluck(voices[ORDER[k % 8]] + 12)
                gain = .15 * VEL[k % 8] * min(1, .3 + (at - first_pulse) / 4)
                for delay, level, side in ((0, 1, pan), (.375, .35, 1 - pan), (.75, .15, pan)):  # note + two echoes
                    put(note, at + delay, gain * level, side)
                if stage == ANSWERS and k % 4 == 0:
                    put(pluck(voices[ORDER[k % 8]] + 24), at, gain * .3, 1 - pan)
        start += dur

    # Reverb: convolve with three seconds of decaying, slightly dulled noise.
    t = clock(3)
    ir = np.random.default_rng(0).standard_normal((len(t), 2)) * np.exp(-t / .7)[:, None]
    ir = fftconvolve(ir, np.ones((12, 1)) / 12, mode="same")
    ir /= np.sqrt((ir ** 2).sum(0))
    mix += .35 * np.stack([fftconvolve(mix[:, c], ir[:, c])[:len(mix)] for c in (0, 1)], axis=1)

    mix = mix[:int(total * SR)]
    t = clock(total)[:len(mix)]
    mix *= (np.minimum(1, t / 1.5) * np.minimum(1, (total - t) / 4))[:, None]  # fade in, fade out
    return mix / np.abs(mix).max() * 10 ** (-3 / 20)  # peak at -3 dBFS


def main() -> None:
    html = (DEMO / "pipeline_demo.html").read_text()
    beats = [(int(d), int(s)) for d, s in re.findall(r"^\s*\[(\d+), (-?\d+), ['`]", html, re.M)]
    video = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                  str(SILENT)], capture_output=True, text=True, check=True).stdout)
    total = sum(d for d, _ in beats)
    assert beats and abs(total - video) < 1, f"BEATS add up to {total} s but the video is {video:.1f} s; re-record it"
    mix = compose(beats)
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "music.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((mix * 32767).astype("<i2").tobytes())
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(SILENT), "-i", str(wav), "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(OUT)], check=True)
    print(f"{len(beats)} beats, {total} s of music -> {OUT.name} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
