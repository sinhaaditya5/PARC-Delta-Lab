"""Shared figure style for PDX-1 charts (docs, deck, report, video)."""
import matplotlib as mpl

COLORS = {
    "ink": "#1d2433",
    "muted": "#6b7385",
    "grid": "#e3e6ec",
    "primary": "#2456c7",     # deep blue
    "secondary": "#7f93b8",   # slate blue
    "accent": "#e8833a",      # orange (alpha / warnings)
    "target": "#b23a48",      # crimson (11B target)
    "good": "#2e8b57",
    "proton": "#2456c7",
    "electron": "#7f93b8",
    "alpha": "#e8833a",
    "boron": "#7a4fb5",
}


def apply_style() -> None:
    mpl.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10.5,
        "axes.edgecolor": COLORS["muted"],
        "axes.labelcolor": COLORS["ink"],
        "axes.titlesize": 12.5,
        "axes.titleweight": "bold",
        "axes.titlecolor": COLORS["ink"],
        "axes.grid": True,
        "grid.color": COLORS["grid"],
        "grid.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": COLORS["muted"],
        "ytick.color": COLORS["muted"],
        "legend.frameon": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })
