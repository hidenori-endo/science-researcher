#!/usr/bin/env python3
"""experiments/galois-edit — computational probing of candidate invariants
for the edit-distance quadratic barrier (claim combo:galois-edit-distance).

Pure Python stdlib. Corpus, criteria, and verdict rule are pre-registered
in PREREGISTER.md (written before this code was ever run).

Usage: python3 run_experiment.py [--quick]
Output: results.json (raw numbers) + printed summary.
"""
import bisect
import json
import random
import sys
import time

N = 1000          # default string length
BIG_N = 2000      # scaling-check length
TIME_CAP_S = 35 * 60

# ---------------------------------------------------------------- exact DP

def edit_distance(a, b):
    """Levenshtein distance, unit costs. Two-row DP, pure python."""
    m, n = len(a), len(b)
    if n > m:
        a, b, m, n = b, a, n, m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        ai = a[i - 1]
        left = i
        for j in range(1, n + 1):
            best = prev[j] + 1            # deletion
            d = left + 1                  # insertion
            if d < best:
                best = d
            sub = prev[j - 1] + (0 if ai == b[j - 1] else 1)  # match/sub
            if sub < best:
                best = sub
            left = best
            cur[j] = best
        prev = cur
    return prev[n]

# ------------------------------------------------------------- statistics

ALPHA = "0123"

def hist_stat(x, y):
    """C1: half L1 distance between symbol-count vectors."""
    cx, cy = {}, {}
    for ch in x:
        cx[ch] = cx.get(ch, 0) + 1
    for ch in y:
        cy[ch] = cy.get(ch, 0) + 1
    keys = set(cx) | set(cy)
    return sum(abs(cx.get(k, 0) - cy.get(k, 0)) for k in keys) / 2.0

def qgram_counts(s, q):
    return {} if len(s) < q else [
        _qc(s, q) for _ in [0]][0]

def _qc(s, q):
    d = {}
    for i in range(len(s) - q + 1):
        g = s[i:i + q]
        d[g] = d.get(g, 0) + 1
    return d

def qgram_lb(x, y, q=5):
    """C2: Ukkonen-style q-gram lower bound via multiset intersection.

    Each edit operation changes x's q-gram multiset by deleting <= q
    occurrences and inserting <= q, hence the multiset intersection mass
    M = sum_w min(g_x(w), g_y(w)) satisfies M >= N_x - q*e when ED=e.
    Therefore e >= max((N_x - M)/q, (N_y - M)/q).

    NOTE (deviation from PREREGISTER.md): the pre-registered formula
    (N_x+N_y-M)/(q+1) is NOT a valid lower bound (our own corpus
    falsified it: x=y gives LB > 0). This corrected Ukkonen-type bound is
    used instead; usability thresholds unchanged."""
    gx = _qc(x, q)
    gy = _qc(y, q)
    nx = sum(gx.values())
    ny = sum(gy.values())
    m_shared = sum(min(v, gy.get(g, 0)) for g, v in gx.items())
    return max(max(0.0, nx - m_shared), max(0.0, ny - m_shared)) / q

def sample_features(x, y, budget, rng, reps=5):
    """C3 sketch: read `budget` positions per string (uniform, no
    replacement) plus floor(budget/3) length-3 windows. Returns the mean
    feature vector over `reps` independent draws.

    Features (fixed 6-dim): [|count diff|/r for each of 0123],
    matched-index fraction, matched-window fraction."""
    n = min(len(x), len(y))
    fd = md = wf = 0.0
    wins = max(1, budget // 3)
    for _ in range(reps):
        idx = rng.sample(range(n), min(budget, n))
        cx, cy = {}, {}
        match = 0
        for i in idx:
            cx[x[i]] = cx.get(x[i], 0) + 1
            cy[y[i]] = cy.get(y[i], 0) + 1
            if x[i] == y[i]:
                match += 1
        fd += sum(abs(cx.get(a, 0) - cy.get(a, 0)) for a in ALPHA) / len(idx)
        md += match / len(idx)
        wm = 0
        for st in rng.sample(range(n - 2), min(wins, n - 2)):
            if x[st:st + 3] == y[st:st + 3]:
                wm += 1
        wf += wm / min(wins, n - 2)
    return [fd / reps, md / reps, wf / reps]

# ------------------------------------------------------------------ stats

def ranks(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r

def spearman(xs, ys):
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denx = sum((a - mx) ** 2 for a in rx) ** 0.5
    deny = sum((b - my) ** 2 for b in ry) ** 0.5
    return num / (denx * deny) if denx * deny else 0.0

class Ridge:
    """Closed-form ridge regression (small dim), Gaussian elimination."""

    def __init__(self, lam=1e-3):
        self.lam = lam
        self.beta = None

    def fit(self, X, y):
        d = len(X[0])
        n = len(X)
        means = [sum(row[j] for row in X) / n for j in range(d)]
        Xc = [[row[j] - means[j] for j in range(d)] for row in X]
        ym = sum(y) / n
        yc = [v - ym for v in y]
        A = [[sum(Xc[k][i] * Xc[k][j] for k in range(n)) +
              self.lam * n * (i == j) for j in range(d)] for i in range(d)]
        b = [sum(Xc[k][i] * yc[k] for k in range(n)) for i in range(d)]
        # Gauss-Jordan
        M = [A[i] + [b[i]] for i in range(d)]
        for col in range(d):
            piv = max(range(col, d), key=lambda r: abs(M[r][col]))
            M[col], M[piv] = M[piv], M[col]
            pv = M[col][col]
            M[col] = [v / pv for v in M[col]]
            for r2 in range(d):
                if r2 != col and M[r2][col]:
                    f = M[r2][col]
                    M[r2] = [a - f * bb for a, bb in zip(M[r2], M[col])]
        self.beta = [M[i][d] for i in range(d)]
        self.intercept = ym - sum(means[j] * self.beta[j] for j in range(d))

    def predict(self, row):
        return self.intercept + sum(b * v for b, v in zip(self.beta, row))

def isotonic_pav(stat, ed):
    """Best least-squares nondecreasing fit of ed against stat (sorted by
    stat). Returns fitted values aligned to input order."""
    order = sorted(range(len(stat)), key=lambda i: stat[i])
    ys = [ed[i] for i in order]
    blocks = [[v, 1] for v in ys]           # [mean, weight]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            w1, n1 = blocks[i]
            w2, n2 = blocks[i + 1]
            blocks[i] = [(w1 * n1 + w2 * n2) / (n1 + n2), n1 + n2]
            del blocks[i + 1]
            if i > 0:
                i -= 1
        else:
            i += 1
    flat = []
    for mean, cnt in blocks:
        flat.extend([mean] * cnt)
    out = [0.0] * len(stat)
    for pos, orig in enumerate(order):
        out[orig] = flat[pos]
    return out

# ----------------------------------------------------------------- corpus

def gen_corpus():
    pairs = []   # dicts: name, seed, x, y, family, n

    def add(fam, seed, x, y):
        pairs.append({"family": fam, "seed": seed, "x": x, "y": y})

    # 1. rand4: 40 pairs
    for seed in range(1000, 1040):
        rng = random.Random(seed)
        add("rand4", seed, "".join(rng.choice("0123") for _ in range(N)),
            "".join(rng.choice("0123") for _ in range(N)))

    # 2. rand2: 20 pairs
    for seed in range(2000, 2020):
        rng = random.Random(seed)
        add("rand2", seed, "".join(rng.choice("01") for _ in range(N)),
            "".join(rng.choice("01") for _ in range(N)))

    # 3. planted: 30 pairs
    levels = [0.02, 0.05, 0.10, 0.20, 0.30]
    seed = 3000
    for lev in levels:
        for _ in range(6):
            rng = random.Random(seed)
            x = "".join(rng.choice("0123") for _ in range(N))
            s = list(x)
            k = int(lev * N)
            for _ in range(k):
                op = rng.randrange(3)
                p = rng.randrange(len(s))
                if op == 0:                       # substitution
                    s[p] = rng.choice("0123")
                elif op == 1 and len(s) > 1:      # deletion
                    del s[p]
                else:                             # insertion
                    s.insert(p, rng.choice("0123"))
            add("planted", seed, x, "".join(s))
            seed += 1

    # 4. perm: 30 pairs, identical histograms
    seed = 4000
    for kind in ("shuffle", "blockswap", "trans"):
        for t in ([None] * 10 if kind != "trans"
                  else [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]):
            rng = random.Random(seed)
            x = ["01"[rng.randrange(2)] for _ in range(N // 2)] * 2
            y = list(x)
            if kind == "shuffle":
                rng.shuffle(y)
            elif kind == "blockswap":
                b = rng.randrange(1, N // 2)
                y = y[b:] + y[:b]
            else:
                for _ in range(t):
                    p = rng.randrange(N - 1)
                    y[p], y[p + 1] = y[p + 1], y[p]
            add("perm-" + kind, seed, "".join(x), "".join(y))
            seed += 1

    # 5. adv: 6 pairs
    adv_defs = [
        ("0" * N, "0" * (N // 2) + "1" * (N // 2)),
        ("0" * N, "01" * (N // 2)),
        ("0" * (N // 2) + "1" * (N // 2), "1" * (N // 2) + "0" * (N // 2)),
    ]
    seed = 5000
    for x, y in adv_defs:
        add("adv", seed, x, y)
        seed += 1
    for _ in range(3):
        rng = random.Random(seed)
        add("adv-control", seed,
            "".join(rng.choice("0123") for _ in range(N)),
            "".join(rng.choice("0123") for _ in range(N)))
        seed += 1

    # 6. scale: n = 2000
    for seed in range(6000, 6005):
        rng = random.Random(seed)
        add("scale-rand4", seed,
            "".join(rng.choice("0123") for _ in range(BIG_N)),
            "".join(rng.choice("0123") for _ in range(BIG_N)))
    for seed in range(6005, 6010):
        rng = random.Random(seed)
        x = ["01"[rng.randrange(2)] for _ in range(BIG_N // 2)] * 2
        rng.shuffle(x)
        y = list(x)
        rng.shuffle(y)
        add("scale-perm", seed, "".join(x), "".join(y))

    return pairs

BUDGETS = [10, 50, 250]   # read budgets (positions/string), cf. 0.01n/0.05n/0.25n

# ------------------------------------------------------------------- main

def main():
    quick = "--quick" in sys.argv
    t0 = time.time()
    pairs = gen_corpus()
    if quick:
        pairs = pairs[:15]
    print(f"corpus: {len(pairs)} pairs")

    rows = []
    for i, p in enumerate(pairs):
        x, y = p["x"], p["y"]
        ed = edit_distance(x, y)
        h = hist_stat(x, y)
        lb5 = qgram_lb(x, y, 5)
        assert lb5 <= ed + 1e-9, (p["family"], p["seed"], ed, lb5)
        rng = random.Random(p["seed"] + 777777)
        feats = {str(b): sample_features(x, y, b, rng) for b in BUDGETS}
        rows.append({
            "family": p["family"], "seed": p["seed"], "n": len(x),
            "ed": ed, "hist": h, "lb5": lb5, "features": feats,
        })
        el = time.time() - t0
        print(f"[{i+1}/{len(pairs)}] {p['family']} seed={p['seed']} "
              f"ED={ed} H={h:.0f} LB5={lb5:.0f} elapsed={el:.0f}s")
        if el > TIME_CAP_S:
            print("TIME CAP HIT — stopping early")
            break

    # ---- C3 fits: train on rand4+planted, evaluate on all n=1000 rows ----
    fit_rows = [r for r in rows if r["family"] in ("rand4", "planted")
                and r["n"] == N]
    eval_rows = [r for r in rows if r["n"] == N]
    c3 = {}
    for b in BUDGETS:
        Xtr = [r["features"][str(b)] for r in fit_rows]
        ytr = [r["ed"] / r["n"] for r in fit_rows]
        mdl = Ridge()
        mdl.fit(Xtr, ytr)
        # model predicts ED/n; convert back to absolute predicted ED
        preds = [mdl.predict(r["features"][str(b)]) * r["n"]
                 for r in eval_rows]
        truth = [r["ed"] for r in eval_rows]
        rho = spearman(preds, truth)
        # near/far classification
        err_all = []
        err_by_fam = {}
        for pred, r in zip(preds, eval_rows):
            lab_t = "near" if r["ed"] <= 0.1 * r["n"] else (
                "far" if r["ed"] >= 0.4 * r["n"] else None)
            if lab_t:
                lab_p = "near" if pred <= 0.25 * r["n"] else "far"
                e = lab_p != lab_t
                err_all.append(e)
                err_by_fam.setdefault(r["family"], []).append(e)
        c3[str(b)] = {
            "spearman_on_eval": round(rho, 4),
            "cls_err_nearfar": round(sum(err_all) / len(err_all), 4),
            "n_classified": len(err_all),
            "cls_err_by_family": {
                fam: round(sum(e) / len(e), 4)
                for fam, e in sorted(err_by_fam.items())},
        }

    # ---- C2 tightness ----
    c2_by_fam = {}
    for r in eval_rows:
        if r["lb5"] >= 1:
            c2_by_fam.setdefault(r["family"], []).append(r["ed"] / r["lb5"])
    c2_summary = {
        fam: {"median_ratio": round(sorted(v)[len(v) // 2], 2),
              "max_ratio": round(max(v), 2), "count": len(v)}
        for fam, v in sorted(c2_by_fam.items())}
    rho_lb = spearman([r["lb5"] for r in eval_rows],
                      [r["ed"] for r in eval_rows])
    rho_h = spearman([r["hist"] for r in eval_rows],
                     [r["ed"] for r in eval_rows])

    # ---- usability: isotonic fit of ED on statistic (train rand4+planted,
    #      worst-case rel. error on full corpus) ----
    def usability(stat_key):
        tr = sorted(fit_rows, key=lambda r: r[stat_key])
        # piecewise-constant monotone lookup via isotonic on train
        fit_vals = isotonic_pav([r[stat_key] for r in tr],
                                [r["ed"] for r in tr])
        stats = [t[stat_key] for t in tr]

        def predict(v):
            # nearest training point by statistic (piecewise-constant interp)
            j = bisect.bisect_left(stats, v)
            cand = [k for k in (j - 1, j) if 0 <= k < len(tr)]
            best_k = min(cand, key=lambda k: abs(stats[k] - v))
            return fit_vals[best_k]
        errs = []
        for r in eval_rows:
            if r["ed"] == 0:
                continue    # relative error undefined for identical pairs
            pe = max(predict(r[stat_key]), 1e-9)
            e = max(pe / r["ed"], r["ed"] / pe)
            errs.append(round(e, 2))
        return {"max_rel_err": max(errs),
                "median_rel_err": round(sorted(errs)[len(errs) // 2], 2)}

    results = {
        "meta": {
            "wall_clock_s": round(time.time() - t0, 1),
            "time_cap_s": TIME_CAP_S,
            "n_pairs": len(rows),
            "budgets": BUDGETS,
        },
        "rows": rows,
        "spearman_full_n1000": {"hist_vs_ed": round(rho_h, 4),
                                "lb5_vs_ed": round(rho_lb, 4)},
        "c2_ratio_by_family": c2_summary,
        "c3_fits": c3,
        "usability_hist": usability("hist"),
        "usability_lb5": usability("lb5"),
    }
    with open("results.json", "w") as f:
        json.dump(results, f, indent=1)

    print("\n=== summary ===")
    print("spearman full corpus (n=1000): hist %.4f  lb5 %.4f"
          % (rho_h, rho_lb))
    print("C2 ED/LB5 ratios:", json.dumps(c2_summary, indent=1))
    print("C3 fits:", json.dumps(c3, indent=1))
    print("usability hist:", results["usability_hist"])
    print("usability lb5 :", results["usability_lb5"])
    print("wall clock: %.1fs" % results["meta"]["wall_clock_s"])

if __name__ == "__main__":
    main()
