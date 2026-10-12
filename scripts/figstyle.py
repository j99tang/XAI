"""House style for publication figures (scientific-figure-making skill conventions).

Centralises what every figure script would otherwise re-declare: the semantic palette,
the matplotlib rcParams preset, and a save helper that emits both a raster and a vector
copy. Figure scripts import from here so a style change lands in one place rather than
seven.

rcParams are matplotlib's global defaults — setting them once at import time means each
script does not repeat font and spine setup, and every figure in the thesis matches.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

# Non-interactive backend: these scripts run headless (no display), and selecting the
# backend must happen BEFORE pyplot is imported or matplotlib picks one itself.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Semantic palette. Blues = the proposed/key method, greens = positive outcomes,
# reds = contrasts/baselines, neutral = background, highlight = ONE callout per figure.
PALETTE = {
    "blue_main": "#0F4D92", "blue_secondary": "#3775BA",
    "green_1": "#DDF3DE", "green_2": "#AADCA9", "green_3": "#8BCF8B",
    "red_1": "#F6CFCB", "red_2": "#E9A6A1", "red_strong": "#B64342",
    "neutral": "#CFCECE", "highlight": "#FFD700",
    "teal": "#42949E", "violet": "#9A4D8E",
    "ink": "#272727", "mute": "#767676",
}
DEFAULT_COLORS = [PALETTE[k] for k in
                  ("blue_main", "green_3", "red_strong", "teal", "violet", "neutral")]


@dataclass(frozen=True)
class FigureStyle:
    font_size: int = 16          # 24 for large bar panels, 15-16 for compact plots
    axes_linewidth: float = 2.5  # 3 for big bars, 2 for compact
    use_tex: bool = False        # only with a working LaTeX install
    font_family: tuple[str, ...] = ("Arial", "Helvetica", "DejaVu Sans", "sans-serif")


def apply_publication_style(style: FigureStyle | None = None) -> None:
    """Set the global rcParams. Call once before creating any figure."""
    s = style or FigureStyle()
    plt.rcParams.update({
        "font.family": list(s.font_family),
        "font.size": s.font_size,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": s.axes_linewidth,
        "legend.frameon": False,
        # keeps text as text in SVG/PDF rather than outlines, so a co-author can
        # restyle labels in Illustrator without re-running the script
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "text.usetex": s.use_tex,
    })


def finalize_figure(fig, out_path, formats=("png", "pdf"), dpi: int = 300,
                    pad: float = 2.0, close: bool = True) -> list[Path]:
    """tight_layout, then save one copy per format. Returns the paths written.

    PNG for slides and the repo README; PDF because a thesis typesets vector art
    without resampling artefacts at print size.
    """
    out = Path(out_path).with_suffix("")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=pad)
    written = []
    for fmt in formats:
        p = out.with_suffix(f".{fmt}")
        fig.savefig(p, dpi=dpi, format=fmt, bbox_inches="tight",
                    pad_inches=0.05, facecolor="white")
        written.append(p)
    if close:
        plt.close(fig)
    return written
