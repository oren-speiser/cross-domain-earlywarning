"""
analysis/engine.py - Turbofan engine domain (NASA C-MAPSS, subset FD001).

Public benchmark (high-fidelity simulation): 100 engines run to failure, 21 sensors.
Health margin is built transparently from the raw sensors (z-score the informative
ones, sign-align to degradation, average), then the SHARED detector is applied.

Source data : https://raw.githubusercontent.com/hankroark/Turbofan-Engine-Degradation
Canonical    : NASA PCoE / https://data.nasa.gov  (C-MAPSS, Saxena & Goebel 2008)
"""
import sys, os, json, urllib.request
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector as D

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW  = os.path.join(ROOT, "raw_data"); os.makedirs(RAW, exist_ok=True)
SRC  = "https://raw.githubusercontent.com/hankroark/Turbofan-Engine-Degradation/master/CMAPSSData/train_FD001.txt"
TXT  = os.path.join(RAW, "train_FD001.txt")
HORIZON = 30

if not os.path.exists(TXT):
    print("downloading C-MAPSS FD001 ..."); urllib.request.urlretrieve(SRC, TXT)

raw = np.loadtxt(TXT)
unit = raw[:, 0].astype(int); cyc = raw[:, 1].astype(int); sens = raw[:, 5:26]
keep = sens.std(0) > 1e-6                      # drop constant sensors
Z = (sens[:, keep] - sens[:, keep].mean(0)) / sens[:, keep].std(0)
units = np.unique(unit)
life_frac = np.zeros(len(unit))
for u in units:
    m = unit == u; c = cyc[m]; life_frac[m] = (c - 1) / (c.max() - 1 + 1e-9)
sign = np.array([np.sign(np.corrcoef(Z[:, j], life_frac)[0, 1]) for j in range(Z.shape[1])]); sign[sign == 0] = 1
Dindex = (Z * sign).mean(1)                    # degradation index: rises toward failure
D_FAIL = float(np.median([Dindex[unit == u][-1] for u in units]))   # population failure level

records = []
for u in units:
    margin = D_FAIL - Dindex[unit == u]        # health margin: falls toward 0 at failure
    M, ttx, warn = D.detect(margin, horizon=HORIZON, rate_win=20)
    fail = len(margin) - 1
    records.append(dict(u=int(u), life=fail + 1, warn=warn, fail=fail, margin=margin, M=M, ttx=ttx))

leads = [r["fail"] - r["warn"] for r in records if r["warn"] is not None and r["fail"] - r["warn"] > 0]
warned = [r for r in records if r["warn"] is not None]
wpl = [100 * r["warn"] / r["life"] for r in warned]
print(f"engines warned with positive lead : {len(leads)}/100")
print(f"lead-time (cycles)                : median {np.median(leads):.0f}  IQR [{np.percentile(leads,25):.0f},{np.percentile(leads,75):.0f}]")
print(f"alarm fires at                    : median {np.median(wpl):.0f}% of life")

# processed data for the demo (6 representative engines)
picks = [34, 58, 87, 71, 78, 95]
out = []
for u in picks:
    r = next(x for x in records if x["u"] == u)
    out.append(dict(id=u, label=f"Engine {u}", life=r["life"], warn=r["warn"], fail=r["fail"],
                    margin=[round(float(x), 3) for x in r["M"]],
                    ttx=[round(float(min(t, 80)), 1) if t > 0 else 80.0 for t in r["ttx"]]))
json.dump(out, open(os.path.join(ROOT, "engine.json"), "w"))

# figure
fig, ax = plt.subplots(1, 1, figsize=(9, 5))
order = sorted(records, key=lambda r: r["life"]); reps = [order[8], order[40], order[70], order[95]]
for r, c in zip(reps, plt.cm.viridis(np.linspace(0.1, 0.85, 4))):
    ax.plot(r["M"], color=c, lw=1.7, label=f"engine {r['u']}")
    if r["warn"] is not None: ax.plot(r["warn"], r["M"][r["warn"]], "o", color="orange", ms=8, mec="k", zorder=5)
    ax.plot(r["fail"], r["margin"][r["fail"]], "v", color="red", ms=8, mec="k", zorder=5)
ax.axhline(0, ls="--", c="k", lw=1, label="failure level"); ax.set_xlabel("engine cycle"); ax.set_ylabel("health margin")
ax.legend(fontsize=8); ax.set_title("Shared ttx detector on NASA C-MAPSS turbofan engines")
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "turbofan_ttx.png"), dpi=130)
print("wrote data/processed/engine.json and figures/turbofan_ttx.png")
