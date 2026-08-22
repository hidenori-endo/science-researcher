#!/usr/bin/env python3
"""2D Ising + FA-type facilitation KCM for combo:prion-glass (AMENDMENT v2).

L x L square lattice, periodic. H = -J sum_<ij> s_i s_j, J = 1.
Instant quench from p=0.5 random state to T < Tc. Heat-bath updates at random
sites; a spin is updated only if it has >= f unlike neighbours *before* the
update (f=0: unconstrained Glauber control). A flip is its own reverse and the
facilitated kernel is the exact conditional of pi, so detailed balance holds
for any f.

Channels (identical Hamiltonian / T / L / quench):
  --f 2  : GLASS  — ordered-domain interiors immobile, conversion at interfaces
  --f 0  : CONTROL— annealed crystallization/coarsening
  --f 3  : ablation

Per checkpoint (log-spaced in t): f_ord (ordered-block fraction), mobility
(facilitated fraction), persistence (never-flipped fraction), cluster stats on
the 3x3-block grid (r_mean, r_max), phi_temp (fraction of newly ordered blocks
4-adjacent to previously ordered blocks) and a placement null.

Pure stdlib. CSV out. Wall-clock guard.
"""
import math
import random
import sys
import time
import os


def build_neighbors(L):
    N = L * L
    nb = [None] * N
    for y in range(L):
        for x in range(L):
            i = y * L + x
            nb[i] = (y * L + ((x + 1) % L),
                     y * L + ((x - 1) % L),
                     ((y + 1) % L) * L + x,
                     ((y - 1) % L) * L + x)
    return nb


def block_grid(L, B):
    """Block index -> list of 9 site indices."""
    cells = []
    for by in range(B):
        for bx in range(B):
            idx = []
            for dy in range(3):
                row = ((by * 3 + dy) % L) * L
                for dx in range(3):
                    idx.append(row + (bx * 3 + dx) % L)
            cells.append(idx)
    return cells


def block_neighbors(B):
    bn = [None] * (B * B)
    for by in range(B):
        for bx in range(B):
            k = by * B + bx
            bn[k] = (by * B + (bx + 1) % B,
                     by * B + (bx - 1) % B,
                     ((by + 1) % B) * B + bx,
                     ((by - 1) % B) * B + bx)
    return bn


def run(f_con, L, T, J, sweeps, seed, out_csv, wall_guard=400.0):
    t_start = time.time()
    rng = random.Random(seed)
    rnd = rng.random
    N = L * L
    B = L // 3
    NB = B * B
    nb = build_neighbors(L)
    cells = block_grid(L, B)
    bnb = block_neighbors(B)

    s = [1 if rnd() < 0.5 else -1 for _ in range(N)]
    ever_flipped = bytearray(N)

    # heat-bath table: P(s_i = +1 | nb_sum), nb_sum in {-4..4}
    pplus = [1.0 / (1.0 + math.exp(-2.0 * J / T * h)) for h in range(-4, 5)]

    rows = []
    prev_ord = None          # set of ordered block ids at previous checkpoint
    prev_sign = None

    def snapshot(t):
        nonlocal prev_ord, prev_sign
        fac = 0
        pers = 0
        for i in range(N):
            n1, n2, n3, n4 = nb[i]
            si = s[i]
            u = ((s[n1] != si) + (s[n2] != si) + (s[n3] != si) + (s[n4] != si))
            if u >= f_con:
                fac += 1
            if not ever_flipped[i]:
                pers += 1
        # blocks
        ord_set = {}
        for k in range(NB):
            c = cells[k]
            msum = s[c[0]] + s[c[1]] + s[c[2]] + s[c[3]] + s[c[4]] + \
                s[c[5]] + s[c[6]] + s[c[7]] + s[c[8]]
            if msum >= 7:
                ord_set[k] = 1
            elif msum <= -7:
                ord_set[k] = -1
        # clusters (same sign, 4-conn)
        areas = []
        rem = set(ord_set)
        while rem:
            start = rem.pop()
            sign = ord_set[start]
            stack = [start]
            area = 0
            while stack:
                k = stack.pop()
                area += 1
                for j in bnb[k]:
                    if j in rem and ord_set[j] == sign:
                        rem.discard(j)
                        stack.append(j)
            areas.append(area)
        nclus = len(areas)
        tot_area = sum(areas)
        r_mean = math.sqrt(tot_area / nclus) if nclus else 0.0
        r_max = math.sqrt(max(areas)) if areas else 0.0

        # templating statistic on newly ordered blocks
        phi_temp = float("nan")
        phi_null = float("nan")
        if prev_ord is not None:
            adj = set()
            for k in prev_ord:
                adj.update(bnb[k])
            new_keys = [k for k in ord_set if k not in prev_ord]
            n_new = len(new_keys)
            if n_new:
                hits = sum(1 for k in new_keys if k in adj)
                phi_temp = hits / n_new
                unordered = [k for k in range(NB) if k not in prev_ord]
                nulls = []
                for _ in range(20):
                    sample = rng.sample(unordered, min(n_new, len(unordered)))
                    nulls.append(sum(1 for k in sample if k in adj) / n_new)
                phi_null = sum(nulls) / len(nulls)

        rows.append((t, fac / N, pers / N, len(ord_set) / NB, nclus,
                     r_mean, r_max, n_new if prev_ord is not None else 0,
                     phi_temp, phi_null, time.time() - t_start))
        prev_ord = set(ord_set)

    def sched():
        t = max(50, sweeps // 400)
        while t < sweeps:
            yield t
            t_next = int(t * 1.12)
            if t_next <= t:
                t_next = t + 1
            t = t_next
        yield sweeps

    snapshot(0)
    t_prev = 0
    for t_chk in sched():
        for _ in range((t_chk - t_prev) * N):
            i = int(rnd() * N)
            si = s[i]
            n1, n2, n3, n4 = nb[i]
            a = s[n1]; b = s[n2]; c = s[n3]; d = s[n4]
            unlike = ((a != si) + (b != si) + (c != si) + (d != si))
            if unlike < f_con:
                continue
            nb_sum = a + b + c + d
            p = pplus[nb_sum + 4]
            ns = 1 if rnd() < p else -1
            if ns != si:
                s[i] = ns
                ever_flipped[i] = 1
        snapshot(t_chk)
        t_prev = t_chk
        if (time.time() - t_start) > wall_guard:
            sys.stderr.write(f"wall guard hit at sweep {t_chk}\n")
            break

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w") as fh:
        fh.write("t,mobility,persistence,f_ord,n_clusters,r_mean,r_max,"
                 "n_new,phi_temp,phi_null,wall_s\n")
        for r in rows:
            fh.write(",".join([
                str(r[0]), f"{r[1]:.6f}", f"{r[2]:.6f}", f"{r[3]:.6f}",
                str(r[4]), f"{r[5]:.4f}", f"{r[6]:.4f}", str(r[7]),
                f"{r[8]:.4f}" if r[8] == r[8] else "nan",
                f"{r[9]:.4f}" if r[9] == r[9] else "nan",
                f"{r[10]:.1f}"]) + "\n")
    print(f"f={f_con} L={L} T={T} sweeps={t_prev} rows={len(rows)} "
          f"wall={time.time()-t_start:.1f}s -> {out_csv}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--f", type=int, default=2, help="facilitation threshold")
    p.add_argument("--L", type=int, default=96)
    p.add_argument("--T", type=float, default=1.5)
    p.add_argument("--J", type=float, default=1.0)
    p.add_argument("--sweeps", type=int, default=20000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", required=True)
    p.add_argument("--wall-guard", type=float, default=400.0)
    a = p.parse_args()
    run(a.f, a.L, a.T, a.J, a.sweeps, a.seed, a.out, a.wall_guard)
