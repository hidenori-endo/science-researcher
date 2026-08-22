#!/usr/bin/env python3
"""combo:cohen-planted-clique — forcing-style world construction experiment.

Worlds at n=1000, k=20 (see PRE_REGISTERED.md):
  W_null   : G(n, 1/2)
  W_clique : G(n, 1/2) + planted K_k
  W_quiet  : G(n, 1/2), planted independent k-set, intra-Q edges rewired outside

Detectors: D1 greedy, D2 spectral power iteration, D3 branch-and-bound search.
Statistics matched between W_clique and W_quiet: mean deg, std deg, max deg,
triangle count. All comparisons via permutation tests.

Pure Python stdlib. Adjacency stored as per-row int bitmasks.
"""

import itertools
import json
import os
import random
import time

N = 1000
K = 20
M = 20                 # draws per world
BUDGET_BNB = 150_000   # node expansions per graph for D3
SPEC_ITERS = 40
PERM_REPS = 20_000
WALL_LIMIT = 40 * 60   # seconds

POP = lambda x: bin(x).count("1")


# ---------------------------------------------------------------- graphs ----

def gen_gnp(n, rng):
    """G(n,1/2) as list of n bitmask rows."""
    adj = []
    for i in range(n):
        r = rng.getrandbits(n)
        r &= ~((1 << (i + 1)) - 1)      # keep bits > i only; symmetrize below
        adj.append(r)
    for i in range(n - 1):
        row = adj[i]
        while row:
            lsb = row & -row
            j = lsb.bit_length() - 1
            adj[j] |= 1 << i
            row ^= lsb
    return adj


def add_edge(adj, u, v):
    adj[u] |= 1 << v
    adj[v] |= 1 << u


def del_edge(adj, u, v):
    adj[u] &= ~(1 << v)
    adj[v] &= ~(1 << u)


def has_edge(adj, u, v):
    return (adj[u] >> v) & 1


def world_null(n, rng):
    return gen_gnp(n, rng), None


def world_clique(n, k, rng):
    adj = gen_gnp(n, rng)
    C = rng.sample(range(n), k)
    for a, b in itertools.combinations(C, 2):
        add_edge(adj, a, b)
    return adj, C


def world_quiet(n, k, rng):
    adj = gen_gnp(n, rng)
    Q = set(rng.sample(range(n), k))
    removed = 0
    for a, b in itertools.combinations(sorted(Q), 2):
        if has_edge(adj, a, b):
            del_edge(adj, a, b)
            removed += 1
    added = 0
    while added < removed:
        u = rng.randrange(n)
        v = rng.randrange(n)
        if u == v or u in Q or v in Q or has_edge(adj, u, v):
            continue
        add_edge(adj, u, v)
        added += 1
    return adj, sorted(Q)


# -------------------------------------------------------------- statistics --

def degree_seq(adj):
    return [POP(r) for r in adj]


def triangles(adj, n):
    total = 0
    for i in range(n):
        row = adj[i]
        ai = adj[i]
        while row:
            lsb = row & -row
            j = lsb.bit_length() - 1
            row ^= lsb
            total += POP(ai & adj[j])
    # each triangle counted once per (ordered edge, third vertex) = 6 times
    if total % 6:
        raise ValueError("triangle count invariant violated")
    return total // 6


def graph_stats(adj, n):
    d = degree_seq(adj)
    mean_d = sum(d) / n
    var = sum((x - mean_d) ** 2 for x in d) / n
    return {
        "mean_deg": mean_d,
        "std_deg": var ** 0.5,
        "max_deg": max(d),
        "triangles": triangles(adj, n),
    }


# ---------------------------------------------------------------- detectors -

def detector_greedy(adj, n):
    deg = degree_seq(adj)
    start = max(range(n), key=lambda v: deg[v])
    clique_mask = 1 << start
    cand = adj[start]
    size = 1
    while cand:
        best_v, best_score = -1, -1
        m = cand
        while m:
            lsb = m & -m
            v = lsb.bit_length() - 1
            m ^= lsb
            s = POP(adj[v] & cand)
            if s > best_score:
                best_v, best_score = v, s
        if best_score < 0:
            break
        clique_mask |= 1 << best_v
        size += 1
        cand &= adj[best_v]
    return size


def detector_spectral(adj, n, iters=SPEC_ITERS):
    """True power iteration for the Perron vector. The float matvec is
    computed with block-quantized weights: vertices are grouped in 64-blocks,
    each weight (4-bit, values 0..15) is decomposed into BIT masks per bit
    level, so s_i = sum_{j in N(i)} b_j = sum over blocks and bit levels of
    2^l * popcount(adj_word & mask). All heavy ops are C-speed int.bit_count().
    """
    BITS = 4
    W = 64
    nb = (n + W - 1) // W
    full = (1 << W) - 1
    # split rows into 64-bit words once
    words = [[(adj[i] >> (W * c)) & full for c in range(nb)] for i in range(n)]

    deg = degree_seq(adj)
    mx = max(deg) or 1
    b = [max(1, min(15, int(15 * d / mx) + 1)) for d in deg]
    lam = 0.0
    for _ in range(iters):
        masks = [[0] * BITS for _ in range(nb)]
        for c in range(nb):
            lo = c * W
            hi = min(n, lo + W)
            mm = masks[c]
            for t, j in enumerate(range(lo, hi)):
                bj = b[j]
                for l in range(BITS):
                    if (bj >> l) & 1:
                        mm[l] |= 1 << t
        bc = int.bit_count
        s = [0] * n
        for i in range(n):
            wi = words[i]
            tot = 0
            for c in range(nb):
                mm = masks[c]
                x = wi[c]
                if x:
                    acc = 0
                    for l in range(BITS):
                        acc += (x & mm[l]).bit_count() << l
                    tot += acc
            s[i] = tot
        num = sum(bi * si for bi, si in zip(b, s))
        den = sum(bi * bi for bi in b) or 1
        lam = num / den
        smax = max(s)
        if smax == 0:
            break
        b = [max(1, min(15, int(15 * si / smax) + 1)) for si in s]
    total = sum(b) or 1
    peak_to_mean = max(b) / (total / n)
    return {"lambda": lam, "localization": peak_to_mean}


def detector_bnb(adj, n, k, node_budget=BUDGET_BNB):
    """Branch-and-bound clique search, early stop at size >= k."""
    deg = degree_seq(adj)
    order = sorted(range(n), key=lambda v: -deg[v])
    best = 0
    nodes = 0

    def expand(clique_size, clique_mask, cand):
        nonlocal best, nodes
        if nodes >= node_budget or best >= k:
            return
        nodes += 1
        if clique_size > best:
            best = clique_size
            if best >= k:
                return
        nc = POP(cand)
        if clique_size + nc <= best:
            return
        # candidates ordered by connectivity within cand (desc)
        cands = []
        m = cand
        while m:
            lsb = m & -m
            v = lsb.bit_length() - 1
            m ^= lsb
            cands.append((POP(adj[v] & cand), v))
        cands.sort(reverse=True)
        for _, v in cands:
            if nodes >= node_budget or best >= k:
                return
            new_cand = cand & adj[v]
            expand(clique_size + 1, clique_mask | (1 << v), new_cand)
            cand &= ~(1 << v)
            if clique_size + POP(cand) <= best:
                return

    for root in order:
        if nodes >= node_budget or best >= k:
            break
        expand(1, 1 << root, adj[root])
    return best


# --------------------------------------------------------- permutation test -

def perm_test(xs, ys, reps=PERM_REPS, seed=0, two_sided=False):
    rng = random.Random(seed)
    nx, ny = len(xs), len(ys)
    obs = sum(xs) / nx - sum(ys) / ny
    pool = list(xs) + list(ys)
    cnt = 0
    for _ in range(reps):
        rng.shuffle(pool)
        diff = sum(pool[:nx]) / nx - sum(pool[nx:]) / ny
        if two_sided:
            if abs(diff) >= abs(obs):
                cnt += 1
        elif diff >= obs:
            cnt += 1
    p = (cnt + 1) / (reps + 1)
    return p, obs


# --------------------------------------------------------------------- main -

def main():
    t0 = time.time()
    worlds = {}
    for wname, builder in [
        ("null", lambda i: world_null(N, random.Random(f"null-{i}"))),
        ("clique", lambda i: world_clique(N, K, random.Random(f"clique-{i}"))),
        ("quiet", lambda i: world_quiet(N, K, random.Random(f"quiet-{i}"))),
    ]:
        recs = []
        for i in range(M):
            adj, plant = builder(i)
            st = graph_stats(adj, N)
            g = detector_greedy(adj, N)
            sp = detector_spectral(adj, N)
            bb = detector_bnb(adj, N, K)
            recs.append({
                "trial": i,
                "stats": st,
                "greedy": g,
                "spec_lambda": sp["lambda"],
                "spec_loc": sp["localization"],
                "bnb": bb,
                "elapsed_s": round(time.time() - t0, 1),
            })
            print(f"[{wname} {i+1}/{M}] tri={st['triangles']} "
                  f"greedy={g} loc={sp['localization']:.2f} bnb={bb} "
                  f"t={recs[-1]['elapsed_s']}s", flush=True)
        worlds[wname] = recs

    elapsed = time.time() - t0

    # ---- statistics matching: W_clique vs W_quiet -------------------------
    stat_names = ["mean_deg", "std_deg", "max_deg", "triangles"]
    matching = {}
    for sn in stat_names:
        xs = [r["stats"][sn] for r in worlds["clique"]]
        ys = [r["stats"][sn] for r in worlds["quiet"]]
        p, obs = perm_test(xs, ys, seed=f"match-{sn}", two_sided=True)
        matching[sn] = {"p_two_sided": round(p, 4),
                        "mean_clique": round(sum(xs)/len(xs), 3),
                        "mean_quiet": round(sum(ys)/len(ys), 3),
                        "matched_ge_0.05": p >= 0.05}

    # ---- detector separation ---------------------------------------------
    def sep(det, alpha, one_sided, tag):
        out = {}
        pairs = [("clique", "quiet"), ("clique", "null"), ("quiet", "null")]
        for a, bname in pairs:
            xs = [r[det] for r in worlds[a]]
            ys = [r[det] for r in worlds[bname]]
            p, obs = perm_test(xs, ys, seed=f"{tag}-{a}-{bname}",
                               two_sided=not one_sided)
            out[f"{a}_vs_{bname}"] = {
                "p": round(p, 5), "delta": round(obs, 4),
                "separates": bool(p < alpha and (obs > 0 if one_sided else True)),
            }
        out["clique_vs_quiet_separated"] = (
            out["clique_vs_quiet"]["separates"])
        return out

    results = {
        "config": {"n": N, "k": K, "m_per_world": M,
                   "bnb_node_budget": BUDGET_BNB,
                   "spectral_iters": SPEC_ITERS,
                   "perm_reps": PERM_REPS},
        "runtime_s": round(elapsed, 1),
        "worlds": worlds,
        "stat_matching": matching,
        "detectors": {
            "D1_greedy": sep("greedy", 0.01, True, "d1"),
            "D3_bnb": sep("bnb", 0.01, True, "d3"),
            "D2_spec_lambda": sep("spec_lambda", 0.005, False, "d2l"),
            "D2_spec_localization": sep("spec_loc", 0.005, False, "d2s"),
        },
    }

    stats_ok = all(v["matched_ge_0.05"] for v in matching.values())
    separated = {k: v["clique_vs_quiet_separated"]
                 for k, v in results["detectors"].items()}
    if not stats_ok:
        verdict = "INCONCLUSIVE"
    elif any(separated.values()):
        verdict = "SUPPORT"
    else:
        verdict = "AGAINST"

    results["stats_matched"] = stats_ok
    results["separation"] = separated
    results["verdict"] = verdict

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)

    print(json.dumps({k: results[k] for k in
                      ("stat_matching", "separation", "verdict",
                       "runtime_s")}, indent=1))


if __name__ == "__main__":
    main()
