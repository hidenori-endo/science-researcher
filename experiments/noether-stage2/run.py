"""Stage-2 driver: run symmetry engine vs template baseline on an extracted
SV-COMP loop corpus under identical parse filters."""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from engine import degree, pstr
from parse_c import extract_file
from symmetry import run_symmetry
from baseline import run_baseline


def maxdeg_claim(claims):
    return max((degree(c["poly"]) for c in claims), default=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="/tmp/svbench-stage2/c")
    ap.add_argument("--out", default="results.json")
    ap.add_argument("--limit-files", type=int, default=100000)
    ap.add_argument("--limit-loops", type=int, default=100000)
    ap.add_argument("--time-budget-s", type=float, default=2100,
                    help="stop processing files beyond this wall budget")
    args = ap.parse_args()

    files = sorted(Path(args.corpus).rglob("*.c")) + \
        sorted(Path(args.corpus).rglob("*.i"))
    print(f"corpus files: {len(files)}")

    stats = Counter()
    loops = []
    t0 = time.time()
    for i, f in enumerate(files[:args.limit_files]):
        got = extract_file(str(f), stats)
        for lp in got:
            lp.name = f"{f.parent.name}/{f.stem}"
            lp.source = str(f)
        loops.extend(got)
        if i % 50 == 0:
            print(f"  [{i}] parsed={len(loops)} elapsed={time.time()-t0:.0f}s")
        if time.time() - t0 > args.time_budget_s * 0.4:
            print(f"  parse budget reached at file {i}")
            break

    print(f"extracted loops: {len(loops)}")
    if args.limit_loops < len(loops):
        print(f"  capping evaluation to first {args.limit_loops} loops")
        loops = loops[:args.limit_loops]
    print("skip reasons:")
    for k, v in sorted(stats.items()):
        if k not in ("loops-extracted", "whiles-found", "functions",
                     "duplicates"):
            print(f"  {k}: {v}")

    # -------------------------------------------------- run both methods
    rows = []
    t_sym_s = t_sym_e = t_base = 0.0
    t1 = time.time()
    for j, lp in enumerate(loops):
        ta = time.time()
        try:
            sym = run_symmetry(lp, mode="strict")
            tb = time.time()
            sym_ext = run_symmetry(lp, mode="extended")
            tc = time.time()
            base = run_baseline(lp, include_eigen=True)
            td = time.time()
        except RecursionError:
            continue
        except Exception as e:
            rows.append({"loop": lp.name, "error": f"{type(e).__name__}"})
            continue
        t_sym_s += tb - ta
        t_sym_e += tc - tb
        t_base += td - tc
        sym_claims = sym["claims"]
        ext_claims = sym_ext["claims"]
        base_claims = base["claims"]
        eig_claims = base.get("eigen_claims", [])
        all_base = base_claims + eig_claims
        nl_sym = any(degree(c["poly"]) >= 2 for c in sym_claims)
        row = {
            "loop": lp.name,
            "nvars": lp.n, "nbranches": len(lp.branches),
            "params": len(lp.params),
            "sym_nsyms": sym["n_syms"],
            "sym_claims": [f"{pstr(c['poly'], lp.vars)} == {c['const']}"
                           for c in sym_claims],
            "symext_claims": [f"{pstr(c['poly'], lp.vars)} == {c['const']}"
                              for c in ext_claims],
            "sym_maxdeg": maxdeg_claim(sym_claims),
            "base_claims": [f"{pstr(c['poly'], lp.vars)} == {c['const']}"
                            for c in base_claims],
            "base_eigen_claims": [f"{pstr(c['poly'], lp.vars)} == {c['const']}"
                                  for c in eig_claims],
            "base_maxdeg": maxdeg_claim(all_base),
            "sym_hit": bool(sym_claims),
            "symext_hit": bool(ext_claims),
            "basecons_hit": bool(base_claims),
            "base_hit": bool(all_base),
            "nonlinear_win": bool(nl_sym and not all_base),
        }
        rows.append(row)
        if j % 25 == 0:
            print(f"  [{j}/{len(loops)}] elapsed={time.time()-t1:.0f}s")
        if time.time() - t1 > args.time_budget_s:
            print(f"  ENGINE time budget reached at loop {j}; stopping")
            rows.append({"truncated": True, "at": j})
            break

    done = [r for r in rows if "sym_hit" in r]
    n = len(done)
    sym_hits = sum(r["sym_hit"] for r in done)
    symext_hits = sum(r["symext_hit"] for r in done)
    base_hits = sum(r["base_hit"] for r in done)
    basecons_hits = sum(r["basecons_hit"] for r in done)
    both_hits = sum(r["sym_hit"] and r["base_hit"] for r in done)
    sym_only = sum(r["sym_hit"] and not r["base_hit"] for r in done)
    base_only = sum(r["base_hit"] and not r["sym_hit"] for r in done)
    nl_wins = sum(r["nonlinear_win"] for r in done)

    summary = {
        "files_seen": min(len(files), args.limit_files),
        "whiles_found": stats["whiles-found"],
        "loops_extracted": stats["loops-extracted"],
        "duplicates_removed": stats["duplicates"],
        "parsed_loops_evaluated": n,
        "skip_reasons": {k: v for k, v in sorted(stats.items())
                         if k not in ("loops-extracted", "whiles-found",
                                      "functions")},
        "coverage": {
            "symmetry_strict": sym_hits / n if n else 0,
            "symmetry_extended": symext_hits / n if n else 0,
            "baseline_conserved_only": basecons_hits / n if n else 0,
            "baseline_conserved_plus_eigen": base_hits / n if n else 0,
        },
        "counts": {
            "symmetry_strict_hits": sym_hits,
            "symmetry_extended_hits": symext_hits,
            "baseline_conserved_hits": basecons_hits,
            "baseline_hits": base_hits,
            "both_methods": both_hits,
            "symmetry_strict_only": sym_only,
            "baseline_only": base_only,
            "nonlinear_wins": nl_wins,
        },
        "runtime_s": {
            "symmetry_engine_strict": round(t_sym_s, 1),
            "symmetry_engine_translation_half": round(t_sym_e, 1),
            "baseline": round(t_base, 1),
        },
    }

    print(json.dumps(summary, indent=2))
    Path(args.out).write_text(json.dumps(
        {"summary": summary, "rows": rows}, indent=1))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
