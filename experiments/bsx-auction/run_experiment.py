"""Run the bsx-auction falsification experiment.

Pure stdlib. Runtime capped (hard wall ~40 min; expected < 2 min).
Usage: python3 run_experiment.py [--quick]
Writes results.json and prints a markdown table.
Cells report CR_mean / CR_worstseed against the clairvoyant optimal fixed price.
For permutation families, CR is the WORST instance (adversarial order) of:
  - cr_mean      : mean policy revenue over 3 repetitions / opt
  - cr_worstseed : max over repetitions of per-run CR, then worst instance
"""

import json
import random
import sys
import time

import families
import policies

CR_CAP = 1000.0
WALL_LIMIT = 40 * 60  # seconds


def run_one(policy, values, grid):
    total = 0.0
    for t in range(1, len(values) + 1):
        idx = policy.choose(t)
        p = grid[idx]
        v = values[t - 1]
        if v >= p:
            rev = p
        else:
            rev = 0.0
        total += rev
        policy.update(idx, rev, rev > 0)
    return total


def seed_for(pname, fname, label):
    # deterministic, stable across runs
    h = 0
    for ch in f"{pname}|{fname}|{label}":
        h = (h * 1000003 + ord(ch)) & 0xFFFFFFFF
    return h


def main():
    quick = "--quick" in sys.argv
    n_seeds = 10 if quick else families.N_IID_SEEDS
    reps_perm = 3
    t0 = time.perf_counter()

    grid = policies.make_grid(16)
    T = families.T
    facs = {
        "uniform-mix": lambda g: policies.UniformMix(g),
        "exp3": lambda g: policies.Exp3(g, T),
        "exp3-anytime": lambda g: policies.Exp3Anytime(g),
        "eps-greedy": lambda g: policies.EpsGreedy(g),
        "ucb1": lambda g: policies.UCB1(g),
    }
    names = list(facs)

    results = {"T": T, "grid": grid, "families": {}, "meta": {}}

    iid_defs = {
        "uniform01": families._uniform01,
        "powlaw": families._powlaw,
        "bimodal": families._bimodal,
        "lognormal": families._lognormal,
    }

    for fname, gen in iid_defs.items():
        streams = [gen(s) for s in range(n_seeds)]
        best_p, opt_per_round = families.best_fixed_iid(streams)
        opt = opt_per_round * T  # clairvoyant TOTAL revenue over the horizon
        pool = [v for s in streams for v in s]
        g_opt = T * max(p * sum(1 for v in pool if v >= p) / len(pool)
                        for p in grid)
        fam = {"kind": "iid", "opt_fixed": round(opt, 5),
               "opt_grid": round(g_opt, 5), "best_p": round(best_p, 4),
               "seeds": n_seeds}
        for pname in names:
            crs, revs = [], []
            for si, s in enumerate(streams):
                random.seed(seed_for(pname, fname, str(si)))
                pol = facs[pname](grid)
                rev = run_one(pol, s, grid)
                revs.append(rev)
                crs.append(opt / rev if rev > 0 else float("inf"))
            mean_rev = sum(revs) / len(revs)
            mean_cr = opt / mean_rev if mean_rev > 0 else float("inf")
            worst_cr = min(max(crs), CR_CAP)
            fam[pname] = {"mean_rev": round(mean_rev, 3),
                          "cr_mean": round(mean_cr, 4),
                          "cr_worstseed": round(worst_cr, 2)}
        results["families"][fname] = fam

    perm_inst = families.perm_instances()
    for fname, insts in perm_inst.items():
        multiset = families.perm_multisets()[fname]
        best_p, opt = families.best_fixed_multiset(multiset)
        g_opt = max(p * sum(1 for x in multiset if x >= p) for p in grid)
        fam = {"kind": "perm", "opt_fixed": opt, "opt_grid": float(g_opt),
               "best_p": round(best_p, 4),
               "instances": [lab for lab, _ in insts]}
        for pname in names:
            per_inst_mean_cr = []
            per_inst_worst_cr = []
            for lab, vals in insts:
                revs = []
                for rep in range(reps_perm):
                    random.seed(seed_for(pname, fname, f"{lab}-{rep}"))
                    pol = facs[pname](grid)
                    revs.append(run_one(pol, vals, grid))
                mean_rev = sum(revs) / len(revs)
                per_inst_mean_cr.append(
                    opt / mean_rev if mean_rev > 0 else CR_CAP * 10)
                worst_run_cr = min(CR_CAP,
                                   max(opt / r if r > 0 else CR_CAP * 10
                                       for r in revs))
                per_inst_worst_cr.append(worst_run_cr)
            fam[pname] = {
                "cr_worst_instance_mean":
                    round(min(CR_CAP, max(per_inst_mean_cr)), 4),
                "cr_worstseed": round(min(CR_CAP, max(per_inst_worst_cr)), 2),
                "cr_best_instance": round(min(per_inst_mean_cr), 4),
            }
        results["families"][fname] = fam

    elapsed = time.perf_counter() - t0
    results["meta"]["elapsed_seconds"] = round(elapsed, 1)
    results["meta"]["n_iid_seeds"] = n_seeds
    results["meta"]["reps_per_perm_instance"] = reps_perm

    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"# runtime: {elapsed:.1f}s\n")
    hdr = "| family | " + " | ".join(names) + " | opt-fixed | opt-grid |"
    print(hdr)
    print("|---" * (len(names) + 3) + "|")
    for fname, fam in results["families"].items():
        cells = []
        for pname in names:
            e = fam.get(pname)
            if e is None:
                cells.append("-")
            elif fam["kind"] == "iid":
                cells.append(f"{e['cr_mean']:.2f} / {e['cr_worstseed']:.1f}")
            else:
                cells.append(f"{e['cr_worst_instance_mean']:.2f} / "
                             f"{e['cr_worstseed']:.1f}")
        print(f"| {fname} | " + " | ".join(cells) +
              f" | {fam['opt_fixed']:.4f} | {fam['opt_grid']:.4f} |")
    print("\ncells: CR_mean(or worst-instance-mean) / CR_worstseed")


if __name__ == "__main__":
    main()
