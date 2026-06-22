"""
detector.py - the single early-warning detector used across all three domains.

One law, many systems: track a HEALTH MARGIN that erodes toward a failure level,
estimate the local rate of erosion, project the time-to-exhaustion (ttx), and raise
a *latched* warning when the projection drops below a horizon.

The math is identical in every domain. Only two things change per domain:
  (1) how the scalar health margin is built from that domain's raw sensors, and
  (2) the smoothing / slope windows, scaled to each domain's sampling interval
      (battery ~1 reading per cycle; bearing 1 reading per 10 s; etc.).
"""
import numpy as np


def smooth(x, med_w=7, ma_w=3):
    """Causal rolling median (robust to spikes / capacity regeneration), then a short MA."""
    x = np.asarray(x, float)
    med = np.array([np.median(x[max(0, i - med_w + 1):i + 1]) for i in range(len(x))])
    return np.array([med[max(0, i - ma_w + 1):i + 1].mean() for i in range(len(med))])


def loss_rate(margin, win=20, floor=1e-4):
    """Trailing-window linear-fit slope of the margin, returned as a positive loss rate."""
    margin = np.asarray(margin, float)
    r = np.full(len(margin), floor)
    for i in range(len(margin)):
        a = max(0, i - win + 1)
        if i - a >= 4:
            slope = np.polyfit(np.arange(a, i + 1), margin[a:i + 1], 1)[0]
            r[i] = max(-slope, floor)          # margin slope is negative while degrading
    return r


def time_to_exhaustion(margin, win=20, floor=1e-4):
    """ttx = remaining margin / current loss rate (projected steps until margin hits 0)."""
    margin = np.asarray(margin, float)
    return margin / loss_rate(margin, win=win, floor=floor)


def latched_warning(ttx, horizon, persist=5):
    """First index where ttx stays inside (0, horizon) for `persist` consecutive readings."""
    below = (ttx > 0) & (ttx < horizon)
    run = 0
    for i in range(len(below)):
        run = run + 1 if below[i] else 0
        if run >= persist:
            return i - persist + 1
    return None


def detect(margin, horizon, med_w=7, ma_w=3, rate_win=20, persist=5):
    """Full pipeline: smooth -> ttx -> latched warning. Returns (smoothed, ttx, warn_index)."""
    m = smooth(margin, med_w, ma_w)
    ttx = time_to_exhaustion(m, win=rate_win)
    warn = latched_warning(ttx, horizon, persist)
    return m, ttx, warn
