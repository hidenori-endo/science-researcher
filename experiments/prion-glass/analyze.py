#!/usr/bin/env python3
"""Analysis + verdict for experiments/prion-glass (AMENDMENT v2 criteria).

Per replica:
  alpha   : OLS slope of log(r_mean) vs log(t) over t >= t_early,
            r_mean in [1.5*r(t_early), 0.93*r_plat], >=6 pts spanning
            >= 0.4 decades in t.
  n       : OLS slope of ln(-ln(1-f_exc)) vs ln(t), f_exc in [0.15,0.70],
            f_exc = (f - f_first)/(f_plat - f_first), f_first = f at t=0.
  phi     : median phi_temp / phi_null over the Avrami window.
Gates: measurability (glass growth ratio >= 1.15 and valid alpha window),
arrest (persistence(GLASS,end) >= 0.10 and > persistence(CONTROL,end)).
Verdict per PRE_REGISTRATION.md amendment v2 (thresholds carried from v1).
"""
import csv
import glob
import json
import math
import os
import sys


def load(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            g = lambda k, cast=float: cast(r[k]) if r[k] != "nan" else None
            rows.append(dict(
                t=float(r["t"]), mobility=float(r["mobility"]),
                persistence=float(r["persistence"]), f=float(r["f_ord"]),
                ncl=int(r["n_clusters"]), r_mean=float(r["r_mean"]),
                r_max=float(r["r_max"]),
                phi_temp=g("phi_temp"), phi_null=g("phi_null")))
    return rows


def ols(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_res = sum((yy - (intercept + slope * xx)) ** 2 for xx, yy in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return slope, r2


def med(v):
    if not v:
        return None
    s = sorted(v)
    m = len(s) // 2
    return s[m] if len(s) % 2 else 0.5 * (s[m - 1] + s[m])


def analyze(path):
    rows = load(path)
    sweeps = rows[-1]["t"]
    # amendment v2.1: anchor at the first log-spaced checkpoint, not 0.05*sweeps
    t_early = next((r["t"] for r in rows if 0 < r["t"]), None)
    ie = next(i for i, r in enumerate(rows) if r["t"] == t_early) if t_early else 0

    f = [r["f"] for r in rows]
    rm = [r["r_mean"] for r in rows]
    tail = max(1, len(rows) * 15 // 100)
    f_plat = sum(f[-tail:]) / tail
    rm_plat = sum(rm[-tail:]) / tail
    out = dict(path=os.path.basename(path), ok=False, sweeps=sweeps,
               f_first=f[0], f_plat=f_plat,
               pers_end=rows[-1]["persistence"], mob_end=rows[-1]["mobility"],
               growth_ratio=(rm[-1] / rm[ie]) if rm[ie] > 0 else None)

    # --- alpha window ---
    lo_r = 1.5 * rm[ie]
    hi_r = 0.93 * rm_plat
    idx = [i for i in range(len(rows))
           if rows[i]["t"] >= t_early and lo_r <= rm[i] <= hi_r]
    if len(idx) >= 6:
        lt = [math.log(rows[i]["t"]) for i in idx]
        lr = [math.log(rm[i]) for i in idx]
        if lt[-1] - lt[0] >= 0.4:
            a, r2 = ols(lt, lr)
            out.update(alpha=a, r2_alpha=r2, n_alpha_pts=len(idx),
                       alpha_span_dec=lt[-1] - lt[0])
        else:
            out["alpha_reason"] = "span < 0.4 decades"
    else:
        out["alpha_reason"] = f"only {len(idx)} pts in window"

    # --- avrami + templating window ---
    idx2 = []
    for i in range(len(rows)):
        if rows[i]["t"] <= 0 or f[i] <= f[0] or f_plat - f[0] <= 0:
            continue
        fe = (f[i] - f[0]) / (f_plat - f[0])
        if 0.15 <= fe <= 0.70:
            idx2.append(i)
    if len(idx2) >= 5:
        lt = [math.log(rows[i]["t"]) for i in idx2]
        try:
            lla = [math.log(-math.log(1 - (f[i] - f[0]) / (f_plat - f[0])))
                   for i in idx2]
        except (ValueError, ZeroDivisionError):
            lla = None
        if lla and len(set(lla)) > 1:
            nv, r2n = ols(lt, lla)
            out.update(navrami=nv, r2_avrami=r2n, n_avrami_pts=len(idx2))
        pt = [rows[i]["phi_temp"] for i in idx2 if rows[i]["phi_temp"] is not None]
        pn = [rows[i]["phi_null"] for i in idx2 if rows[i]["phi_null"] is not None]
        out.update(phi_temp=med(pt), phi_null=med(pn))
    out["ok"] = out.get("alpha") is not None
    return out


def agg(rs, key):
    vals = [r[key] for r in rs if r.get("ok") and r.get(key) is not None]
    if not vals:
        return None, None
    return sum(vals) / len(vals), (min(vals), max(vals))


def main():
    data_dir = sys.argv[1] if len(sys.argv) == 2 and not sys.argv[1].startswith("-") else "data"
    modes = {"glass": [], "control": []}
    ablation = []
    for p in sorted(glob.glob(os.path.join(data_dir, "*.csv"))):
        base = os.path.basename(p)
        r = analyze(p)
        if base.startswith("glass_f3"):
            ablation.append(r)
        elif base.startswith("glass"):
            modes["glass"].append(r)
        elif base.startswith("control"):
            modes["control"].append(r)

    summary = {}
    for mode in ("glass", "control"):
        rs = modes[mode]
        print(f"\n=== {mode} ({len(rs)} replicas) ===")
        for r in rs:
            print(f"  {r['path']}: ok={r['ok']} "
                  f"f:{r['f_first']:.3f}->{r['f_plat']:.3f} "
                  f"pers_end={r['pers_end']:.3f} gr={r['growth_ratio'] and round(r['growth_ratio'],2)} "
                  f"alpha={r.get('alpha') and round(r['alpha'],3)} "
                  f"(R2={r.get('r2_alpha') and round(r['r2_alpha'],4)}, "
                  f"pts={r.get('n_alpha_pts')}, dec={r.get('alpha_span_dec') and round(r['alpha_span_dec'],2)}) "
                  f"n={r.get('navrami') and round(r['navrami'],3)} "
                  f"(R2={r.get('r2_avrami') and round(r['r2_avrami'],4)}) "
                  f"phiT={r.get('phi_temp') and round(r['phi_temp'],3)} "
                  f"phiN={r.get('phi_null') and round(r['phi_null'],3)}"
                  + (f" alpha_reason={r.get('alpha_reason')}" if r.get("alpha_reason") else ""))
        summary[mode] = {}
        for key in ("alpha", "navrami", "phi_temp", "phi_null", "pers_end"):
            m, sp = agg(rs, key)
            summary[mode][key] = m
            summary[mode][key + "_spread"] = sp
        print(f"  MEAN alpha={summary[mode]['alpha']} spread={summary[mode]['alpha_spread']}")
        print(f"       navrami={summary[mode]['navrami']} spread={summary[mode]['navrami_spread']}")
        print(f"       phi_temp={summary[mode]['phi_temp']} spread={summary[mode]['phi_temp_spread']}")
        print(f"       pers_end={summary[mode]['pers_end']}")

    g, c = summary["glass"], summary["control"]
    print("\n=== ABLATION glass f=3 ===")
    for r in ablation:
        print(f"  {r['path']}: ok={r['ok']} f:{r['f_first']:.3f}->{r['f_plat']:.3f} "
              f"gr={r['growth_ratio'] and round(r['growth_ratio'],3)} "
              f"mob_end={r['mob_end']} "
              f"alpha={r.get('alpha') and round(r['alpha'],3)} "
              f"reason={r.get('alpha_reason','-')}")

    print("\n=== GATES ===")
    meas_ok = (g["alpha"] is not None and
               all(r["growth_ratio"] is not None and r["growth_ratio"] >= 1.15
                   for r in modes["glass"]))
    arrest_ok = (g["pers_end"] is not None and c["pers_end"] is not None and
                 g["pers_end"] >= 0.10 and g["pers_end"] > c["pers_end"])
    print(f"  measurability (glass grows, valid window): {meas_ok}")
    print(f"  arrest (pers_glass>=0.10 and > pers_control): {arrest_ok} "
          f"({g['pers_end']} vs {c['pers_end']})")

    alpha_g, alpha_c = g["alpha"], c["alpha"]
    ctrl_sane = alpha_c is not None and 0.40 <= alpha_c <= 0.60
    null_ratio = (g["phi_temp"] / g["phi_null"]
                  if g["phi_temp"] is not None and g["phi_null"] else None)
    checks = {
        "S1 phi_temp(glass)>=0.75": g["phi_temp"] is not None and g["phi_temp"] >= 0.75,
        "S2 null_ratio>=2": null_ratio is not None and null_ratio >= 2.0,
        "S3a alpha_glass+0.06<alpha_ctrl": None not in (alpha_g, alpha_c) and alpha_g + 0.06 < alpha_c,
        "S3b alpha_ctrl in [0.40,0.60]": ctrl_sane,
        "S4 navrami(glass)<1.0": g["navrami"] is not None and g["navrami"] < 1.0,
    }
    a2a = None not in (alpha_g, alpha_c) and abs(alpha_g - alpha_c) <= 0.06
    a2b = g["navrami"] is not None and g["navrami"] >= 2.0
    support = all(checks.values())
    against = ((a2a and ctrl_sane) or a2b)
    verdict = ("SUPPORT" if support else
               "AGAINST" if against else
               "INCONCLUSIVE")
    if not (meas_ok and arrest_ok):
        verdict = "INCONCLUSIVE"
    print("\n=== PRE-REGISTERED VERDICT LOGIC (amendment v2) ===")
    print(f"  null_ratio(glass) = {null_ratio}")
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"  A2a |dAlpha|<=0.06 (ctrl sane): {a2a and ctrl_sane}")
    print(f"  A2b navrami>=2.0: {a2b}")
    print(f"\nVERDICT: {verdict}")

    with open(os.path.join(data_dir, "..", "results.json"), "w") as fh:
        json.dump(dict(summary=summary, checks=checks,
                       gates=dict(measurability=meas_ok, arrest=arrest_ok),
                       null_ratio=null_ratio, verdict=verdict,
                       a2a=a2a, a2b=a2b, ctrl_sane=ctrl_sane,
                       replicas={m: [dict((k, v) for k, v in r.items())
                                        for r in rs]
                                 for m, rs in modes.items()},
                       ablation=ablation),
                  fh, indent=2, default=str)
    return verdict


if __name__ == "__main__":
    main()
