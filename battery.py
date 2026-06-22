"""
analysis/battery.py - Li-ion battery domain (NASA, real measured aging).

Real measured cells B0005/B0006/B0018 cycled to end-of-life (EOL = 1.4 Ah).
Health margin = discharge capacity - EOL. The SHARED detector is applied directly.

Source data : https://raw.githubusercontent.com/XiuzeZhou/NASA  (.mat mirror)
Canonical    : NASA PCoE / https://data.nasa.gov  (Saha & Goebel 2007)
"""
import sys, os, json, urllib.request
import numpy as np, scipy.io as sio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector as D

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW  = os.path.join(ROOT, "raw_data", "battery"); os.makedirs(RAW, exist_ok=True)
SRC  = "https://raw.githubusercontent.com/XiuzeZhou/NASA/main/dataset/"
EOL, HORIZON = 1.4, 15
CELLS = ["B0005", "B0006", "B0018"]            # the three that clearly reach EOL

def caps(name):
    p = os.path.join(RAW, name + ".mat")
    if not os.path.exists(p):
        print("downloading", name + ".mat ..."); urllib.request.urlretrieve(SRC + name + ".mat", p)
    m = sio.loadmat(p, squeeze_me=True, struct_as_record=False)
    return np.array([float(np.atleast_1d(c.data.Capacity)[0])
                     for c in m[name].cycle if c.type == "discharge" and hasattr(c.data, "Capacity")])

out = []
for name in CELLS:
    c = caps(name)
    margin = c - EOL                            # falls toward 0 at EOL
    M, ttx, warn = D.detect(margin, horizon=HORIZON, rate_win=20)
    fail = int(np.argmax(M < 0)) if (M < 0).any() else len(M) - 1
    lead = (fail - warn) if warn is not None else None
    print(f"{name}: life={len(M)} warn={warn} fail={fail} lead={lead}")
    out.append(dict(label=name, life=len(M), warn=warn, fail=fail,
                    margin=[round(float(x), 4) for x in M],
                    ttx=[round(float(min(t, 60)), 1) if t > 0 else 60.0 for t in ttx]))
json.dump(out, open(os.path.join(ROOT, "battery.json"), "w"))
print("wrote data/processed/battery.json")
