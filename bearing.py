"""
analysis/bearing.py - Bearing / rotating-machinery domain (FEMTO PRONOSTIA, real measured).

Real measured run-to-failure vibration. Health indicator = RMS of horizontal
acceleration per 0.1 s snapshot (recorded every 10 s); it rises as the bearing
degrades. Margin = (RMS at failure) - RMS, so it falls toward 0 at failure.
The SHARED detector is applied with wider windows (snapshots are dense, 10 s apart).

Source data : https://github.com/wkzs111/phm-ieee-2012-data-challenge-dataset
Canonical    : FEMTO-ST Institute / IEEE PHM 2012 Prognostic Challenge (Nectoux 2012)
Note: bearings fail ABRUPTLY, so the alarm fires late in life with a short (but real) lead.
"""
import sys, os, json, glob, subprocess
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detector as D

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW  = os.path.join(ROOT, "raw_data", "femto")
REPO = "https://github.com/wkzs111/phm-ieee-2012-data-challenge-dataset.git"
BEARINGS = {"Bearing 1-1": "Bearing1_1", "Bearing 2-1": "Bearing2_1", "Bearing 3-1": "Bearing3_1"}
HORIZON = 60

def fetch():
    """Sparse, blobless checkout of just the three bearings we use (keeps the download small)."""
    if os.path.exists(os.path.join(RAW, "Learning_set", "Bearing1_1")): return
    os.makedirs(os.path.dirname(RAW), exist_ok=True)
    print("sparse-downloading 3 bearings from FEMTO repo ...")
    subprocess.run(["git", "clone", "--no-checkout", "--depth", "1", "--filter=blob:none", REPO, RAW], check=True)
    subprocess.run(["git", "-C", RAW, "sparse-checkout", "init", "--cone"], check=True)
    subprocess.run(["git", "-C", RAW, "sparse-checkout", "set"] + [f"Learning_set/{b}" for b in BEARINGS.values()], check=True)
    subprocess.run(["git", "-C", RAW, "checkout"], check=True)

def rms_traj(folder):
    files = sorted(glob.glob(os.path.join(folder, "acc_*.csv")))
    r = np.empty(len(files))
    for i, f in enumerate(files):
        x = pd.read_csv(f, header=None, usecols=[4]).values[:, 0]   # col 4 = horizontal accel
        r[i] = np.sqrt(np.mean(x * x))
    return r

fetch()
out = []
for label, folder in BEARINGS.items():
    rms = rms_traj(os.path.join(RAW, "Learning_set", folder))
    H = D.smooth(rms, med_w=15, ma_w=4); thr = H[-1]; margin = thr - H
    M, ttx, warn = D.detect(margin, horizon=HORIZON, med_w=15, ma_w=4, rate_win=40)
    fail = len(M) - 1; lead = (fail - warn) if warn is not None else None
    print(f"{label}: snapshots={len(M)} warn={warn} fail={fail} lead={lead} ({None if lead is None else lead*10}s)")
    out.append(dict(label=label, life=len(M), warn=warn, fail=fail,
                    margin=[round(float(x), 4) for x in M],
                    ttx=[round(float(min(t, 80)), 1) if t > 0 else 80.0 for t in ttx]))
json.dump(out, open(os.path.join(ROOT, "bearing.json"), "w"))
print("wrote data/processed/bearing.json")
