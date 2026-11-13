"""Record docs/demo/pipeline_demo.html to docs/demo/pipeline_demo.mp4 (one loop, silent).

Drives headless Chrome over the DevTools protocol, saves each frame Chrome paints together
with its timestamp, then has ffmpeg lay the frames out at a constant 30 fps. Recording is
real time: a 3:43 video takes 3:43 to capture. Needs Chrome, ffmpeg and the fonts (online).

Run: conda run -n xai python scripts/record_demo.py            # full loop
     conda run -n xai python scripts/record_demo.py 15         # first 15 s, as a quick test
"""
from __future__ import annotations
import asyncio, base64, json, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
import websockets

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "demo" / "pipeline_demo.html"
OUT = PAGE.with_suffix(".mp4")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT, FPS = 9333, 30


async def capture(ws, tmp: Path, limit: float | None) -> list[float]:
    """Play the page from beat 0 and save frames until `limit` seconds; return their timestamps."""
    sent, stamps = 0, []

    def on_frame(p) -> None:
        stamps.append(p["metadata"]["timestamp"])
        (tmp / f"f{len(stamps):06d}.jpg").write_bytes(base64.b64decode(p["data"]))

    async def call(method: str, **params):
        nonlocal sent
        sent += 1
        await ws.send(json.dumps({"id": sent, "method": method, "params": params}))
        while True:  # frames can arrive while we wait for the reply; keep them
            msg = json.loads(await ws.recv())
            if msg.get("method") == "Page.screencastFrame":
                on_frame(msg["params"])
                await ws.send(json.dumps({"id": 0, "method": "Page.screencastFrameAck",
                                          "params": {"sessionId": msg["params"]["sessionId"]}}))
            elif msg.get("id") == sent:
                if "error" in msg:
                    raise SystemExit(f"{method} failed: {msg['error']}")
                return msg["result"]

    js = lambda expr: call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
    await call("Page.enable")
    # --window-size includes the browser frame (the page got 1920x993), so pin the viewport itself.
    await call("Emulation.setDeviceMetricsOverride", width=1920, height=1080, deviceScaleFactor=1, mobile=False)
    for _ in range(50):  # wait for the page script, then for the web fonts
        if (await js("typeof total"))["result"].get("value") == "number":
            break
        await asyncio.sleep(.2)
    else:
        raise SystemExit("the demo page did not load (is docs/demo/demo_data.js there?)")
    total = (await js("document.fonts.ready.then(() => total)"))["result"]["value"]
    limit = min(limit or total, total) - .1  # stop just before the loop restarts
    print(f"recording {limit:.0f} s of {total} s ...", flush=True)
    await js("beat = 0; play(true)")
    await call("Page.startScreencast", format="jpeg", quality=95, everyNthFrame=2)
    while not stamps or stamps[-1] - stamps[0] < limit:
        await call("Runtime.evaluate", expression="0")  # a cheap round trip that drains frames
        await asyncio.sleep(.01)
    return stamps, limit


async def main() -> None:
    limit = float(sys.argv[1]) if len(sys.argv) > 1 else None
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        chrome = subprocess.Popen(
            [CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={tmp / 'profile'}",
             "--hide-scrollbars", PAGE.as_uri()],
            stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                    break
                except OSError:
                    time.sleep(.2)
            else:
                raise SystemExit("Chrome did not open its debugging port")
            url = next(t["webSocketDebuggerUrl"] for t in targets if t["type"] == "page")
            async with websockets.connect(url, max_size=None) as ws:
                stamps, limit = await capture(ws, tmp, limit)
        finally:
            chrome.terminate()

        # Chrome paints at an uneven rate, so each frame is held for the time it was really
        # on screen; ffmpeg then resamples that to a constant frame rate.
        ends = stamps[1:] + [stamps[0] + limit + 1 / FPS]
        lines = [f"file 'f{i + 1:06d}.jpg'\nduration {max(e - s, .001):.4f}" for i, (s, e) in enumerate(zip(stamps, ends))]
        (tmp / "list.txt").write_text("\n".join(lines + [f"file 'f{len(stamps):06d}.jpg'"]) + "\n")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                        "-vf", f"fps={FPS}", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(OUT)], check=True)
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    print(f"{len(stamps)} frames captured, longest gap {max(gaps):.2f} s -> {OUT.relative_to(ROOT)} "
          f"({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    asyncio.run(main())
