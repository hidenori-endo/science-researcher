#!/usr/bin/env python3
"""combo:mendel-sex cheap falsification — Muller's ratchet vs free recombination.

Asexual vs sexual (free recombination) Wright-Fisher populations with
multiplicative fitness on an abstract L-locus bitmask genome. Measures the
degradation rate r (slope of ln mean-fitness) for both modes and derives the
mutation-rate threshold U* where recombination's advantage crosses zero and
where it repays the twofold cost of sex (see PREREGISTRATION.md).

Pure Python stdlib. Fixed seeds. Driver enforces a wall-clock budget.
"""
import argparse
import bisect
import json
import math
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
from itertools import accumulate

# ---------------------------------------------------------------- core


def poisson(rng, mean):
    """Knuth's algorithm; fine for mean <= ~5."""
    L = math.exp(-mean)
    k = 0
    p = 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def slope(y):
    """OLS slope of y over x = 0..len(y)-1."""
    n = len(y)
    sx = (n - 1) * n / 2.0
    sxx = (n - 1) * n * (2 * n - 1) / 6.0
    sy = sum(y)
    sxy = sum(i * v for i, v in enumerate(y))
    d = n * sxx - sx * sx
    return (n * sxy - sx * sy) / d


def run_pop(N, s, U, L, T, mode, seed):
    """One population. Returns (r, final_mean_k, clicks, elapsed)."""
    rng = random.Random(seed)
    ALL = (1 << L) - 1
    genomes = [0] * N
    wfac = 1.0 - s
    logw = []          # ln W̄ each generation
    mink_series = []   # least-loaded class level (for ratchet clicks)
    t0 = time.time()
    for _ in range(T + 1):
        ks = [g.bit_count() for g in genomes]
        logw.append(-math.log(1.0 - s) * sum(ks) / N)
        mink_series.append(min(ks))
        # viability selection -> parent indices (multinomial, N draws)
        cum = list(accumulate((wfac ** k for k in ks)))
        tot = cum[-1]
        draw = bisect.bisect_right
        ru = rng.random
        if mode == "asex":
            parents = [draw(cum, ru() * tot) for _ in range(2 * N)]
            children = []
            ap = children.append
            for i in range(0, 2 * N, 2):  # keep draw count identical across modes
                g = genomes[parents[i]]
                n = poisson(rng, U)
                for _ in range(n):
                    g |= 1 << rng.randrange(L)
                ap(g)
        else:  # sex: free recombination, locus-wise from either parent
            parents = [draw(cum, ru() * tot) for _ in range(2 * N)]
            children = []
            ap = children.append
            for i in range(0, 2 * N, 2):
                m = rng.getrandbits(L)
                g = (genomes[parents[i]] & m) | (genomes[parents[i + 1]] & ~m)
                n = poisson(rng, U)
                for _ in range(n):
                    g |= 1 << rng.randrange(L)
                ap(g)
        genomes = children
    elapsed = time.time() - t0
    half = T // 2
    r = slope(logw[half:])
    clicks = sum(
        1
        for a, b in zip(mink_series[half:], mink_series[half + 1:])
        if b > a
    )
    return r, sum(g.bit_count() for g in genomes) / N, clicks, elapsed


def L_for(U, s):
    return int(6 * U / s) + 32


def report(c):
    print(
        f"N={c['N']:5d} s={c['s']:5.3f} U={c['U']:5.2f}  "
        f"r_asex={c['r_asex']:+.3e} r_sex={c['r_sex']:+.3e}  "
        f"A={c['A']:+.3e}±{c['se_A']:.1e}  n0={c['n0_theory']:.3g} "
        f"clicks/1k={c['clicks_asex_per_1k_gen']:.1f} [{c['elapsed_s']:.0f}s]",
        flush=True,
    )


# ---------------------------------------------------------------- driver


def cell(N, s, U, T, reps, seed0):
    L = L_for(U, s)
    rs_a, rs_s = [], []
    el = 0.0
    clicks_a = None
    for rep in range(reps):
        seed = seed0 + rep
        r, mk, cl, e = run_pop(N, s, U, L, T, "asex", seed)
        rs_a.append(r)
        el += e
        clicks_a = cl
        r, mk, _, e = run_pop(N, s, U, L, T, "sex", seed)
        rs_s.append(r)
        el += e
    diffs = [a - sx for a, sx in zip(rs_a, rs_s)]
    mean_a = sum(rs_a) / reps
    mean_s = sum(rs_s) / reps
    A = sum(diffs) / reps
    var = sum((d - A) ** 2 for d in diffs) / max(1, reps - 1)
    se_A = math.sqrt(var / reps)
    return {
        "N": N, "s": s, "U": U, "L": L, "reps": reps,
        "r_asex": mean_a, "r_sex": mean_s, "A": A, "se_A": se_A,
        "clicks_asex_per_1k_gen": 1000.0 * clicks_a / (T // 2),
        "n0_theory": N * math.exp(-U / s),
        "elapsed_s": el,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=2100.0,
                    help="wall-clock budget for the grid (s)")
    ap.add_argument("--T", type=int, default=2000)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--workers", type=int,
                    default=min(8, os.cpu_count() or 1))
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    if args.quick:
        grid = [(500, 0.05, 0.5)]
        T, reps = 300, 1
    else:
        grid = [
            (N, s, U)
            for (N, s) in [(500, 0.05), (2000, 0.05), (2000, 0.02), (5000, 0.02)]
            for U in [0.05, 0.1, 0.2, 0.35, 0.5, 0.8, 1.2, 2.0]
        ]
        T, reps = args.T, args.reps

    seed0 = 20260227
    results = []
    t_start = time.time()
    # Cells are mutually independent with per-cell fixed seeds, so running them
    # in a process pool does not change any sampled value vs a serial run.
    if args.quick or args.workers <= 1:
        for N, s, U in grid:
            c = cell(N, s, U, T, reps, seed0)
            c["skipped_by_budget"] = False
            results.append(c)
            report(c)
    else:
        futures = {}
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            for N, s, U in grid:
                fu = ex.submit(cell, N, s, U, T, reps, seed0)
                futures[fu] = (N, s, U)
            for fu in list(futures):
                try:
                    c = fu.result(timeout=max(60.0, args.budget -
                                              (time.time() - t_start)))
                except Exception:
                    N, s, U = futures[fu]
                    print(f"cell N={N} s={s} U={U}: FAILED/timeout", flush=True)
                    continue
                c["skipped_by_budget"] = False
                results.append(c)
                report(c)
    skipped = [[N, s, U] for (N, s, U) in grid
               if not any(r.get("N") == N and r.get("s") == s and
                          r.get("U") == U and not r.get("skipped_by_budget")
                          for r in results)]
    for sk in skipped:
        results.append({"N": sk[0], "s": sk[1], "U": sk[2],
                        "skipped_by_budget": True})

    total = time.time() - t_start
    out = {
        "T": T, "reps": reps, "seed0": seed0,
        "budget_s": args.budget, "wall_clock_s": total,
        "workers": args.workers,
        "skipped_by_budget": skipped, "cells": results,
    }
    path = "experiments/mendel-sex/results.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\ntotal wall clock: {total:.1f} s (budget {args.budget:.0f} s); "
          f"skipped {len(skipped)} cells; wrote {path}")


if __name__ == "__main__":
    main()
