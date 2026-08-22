#!/usr/bin/env python3
"""2D binary lattice-gas surrogate for combo:prion-glass.

L x L square lattice, periodic. Two species A/B (50:50), density rho.
Hamiltonian: -sum of like-species NN bonds (eps_AA=eps_BB=1, eps_AB=0).
Dynamics: Kawasaki Metropolis (particle hops to a vacant NN), instant quench.

Two dynamics on the IDENTICAL Hamiltonian:
  --mode glass   : hop allowed only if the mover has >= m occupied NN before
                   the move (KA-type kinetic constraint; starves transport of
                   isolated monomers -> suppresses bulk nucleation).
  --mode control : no kinetic constraint (annealed demixing / crystallization).

Local-order observable: a site is ORDERED if occupied with >= 3 occupied NN of
the SAME species (bulk-like environment of the demixed state).

Checkpoints are log-spaced in t (factor 1.12 from t=50) plus every `chk`.
Per checkpoint: ordered fraction f, mobility, cluster stats (r_mean, r_max),
templating fraction of newly ordered sites (adjacent to previously ordered),
and a placement-null (same count sampled uniformly over unordered sites).

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
    for x in range(L):
        for y in range(L):
            i = y * L + x
            nb[i] = (y * L + ((x + 1) % L),
                     y * L + ((x - 1) % L),
                     ((y + 1) % L) * L + x,
                     ((y - 1) % L) * L + x)
    return nb


def init_config(L, rho, rng):
    N = L * L
    lat = [0] * N
    occ = []
    for i in range(N):
        if rng.random() < rho:
            lat[i] = 1 if rng.random() < 0.5 else 2
            occ.append(i)
    return lat, occ


def run(mode, L, rho, T, sweeps, chk, seed, out_csv, wall_guard=600.0, M=2):
    t_start = time.time()
    rng = random.Random(seed)
    rnd = rng.random
    N = L * L
    nb = build_neighbors(L)
    m_con = M
    exp_tab = [math.exp(-d / T) for d in range(-4, 5)]

    lat, occ = init_config(L, rho, rng)
    n_occ = len(occ)

    constrained = (mode == "glass")

    rows = []
    prev_ord = 0

    def like_cnt(i):
        n1, n2, n3, n4 = nb[i]
        s = lat[i]
        return ((lat[n1] == s) + (lat[n2] == s) +
                (lat[n3] == s) + (lat[n4] == s))

    def snapshot(t):
        nonlocal prev_ord
        ordered = 0
        mob = 0
        for i in range(N):
            v = lat[i]
            if not v:
                continue
            n1, n2, n3, n4 = nb[i]
            c = (lat[n1] != 0) + (lat[n2] != 0) + (lat[n3] != 0) + (lat[n4] != 0)
            lc = (lat[n1] == v) + (lat[n2] == v) + (lat[n3] == v) + (lat[n4] == v)
            if c < 4 and c >= m_con:
                mob += 1
            if lc >= 3:
                ordered |= (1 << i)
        # clusters
        areas = []
        rem = ordered
        while rem:
            lsb = rem & -rem
            start = lsb.bit_length() - 1
            rem ^= lsb
            stack = [start]
            area = 0
            while stack:
                s = stack.pop()
                area += 1
                for j in nb[s]:
                    b = 1 << j
                    if rem & b:
                        rem ^= b
                        stack.append(j)
            areas.append(area)
        nclus = len(areas)
        tot_area = sum(areas)
        r_mean = math.sqrt(tot_area / nclus) if nclus else 0.0
        r_max = math.sqrt(max(areas)) if areas else 0.0

        new = ordered & ~prev_ord
        n_new = bin(new).count("1")
        if n_new and prev_ord:
            adj = 0
            mm = prev_ord
            while mm:
                lsb = mm & -mm
                s = lsb.bit_length() - 1
                mm ^= lsb
                for j in nb[s]:
                    adj |= (1 << j)
            hits = bin(new & adj).count("1")
            phi_temp = hits / n_new
            nonprev = [i for i in range(N) if not (prev_ord >> i) & 1]
            nulls = []
            for _ in range(20):
                k = 0
                for s in rng.sample(nonprev, min(n_new, len(nonprev))):
                    if (adj >> s) & 1:
                        k += 1
                nulls.append(k / n_new)
            phi_null = sum(nulls) / len(nulls)
        else:
            phi_temp = float("nan")
            phi_null = float("nan")

        rows.append((t, mob / max(n_occ, 1), bin(ordered).count("1") / N,
                     nclus, r_mean, r_max, n_new, phi_temp, phi_null,
                     time.time() - t_start))
        prev_ord = ordered

    def sched():
        """yield checkpoint times: log-spaced from 50, then every chk"""
        t = 50
        while t < sweeps:
            yield t
            t_next = int(t * 1.12)
            if t_next <= t:
                t_next = t + 1
            if t_next > 10 * chk:
                t_next = ((t_next // chk) + 1) * chk
            t = t_next
        yield sweeps

    snapshot(0)
    t_prev = 0
    for t_chk in sched():
        # evolve from t_prev to t_chk
        for _ in range(t_chk - t_prev):
            for _ in range(N):
                k = int(rnd() * n_occ)
                i = occ[k]
                n1, n2, n3, n4 = nb[i]
                a = lat[n1]; b = lat[n2]; c = lat[n3]; d = lat[n4]
                cnt = (a != 0) + (b != 0) + (c != 0) + (d != 0)
                if cnt >= 4:
                    continue
                if constrained and cnt < m_con:
                    continue
                r = rnd() * 4
                if r < 1.0:
                    j = n1
                elif r < 2.0:
                    j = n2
                elif r < 3.0:
                    j = n3
                else:
                    j = n4
                if lat[j] != 0:
                    continue
                s = lat[i]
                li = (a == s) + (b == s) + (c == s) + (d == s)
                m1, m2, m3, m4 = nb[j]
                lj = ((lat[m1] == s) + (lat[m2] == s) + (lat[m3] == s) +
                      (lat[m4] == s) - 1)  # excl i
                # H=-like_bonds ; dE = -(bonds_after-bonds_before)=li-lj
                dE = li - lj
                if dE > 0 and rnd() >= exp_tab[dE + 4]:
                    continue
                lat[i] = 0
                lat[j] = s
                occ[k] = j
        snapshot(t_chk)
        t_prev = t_chk
        if (time.time() - t_start) > wall_guard:
            sys.stderr.write(f"wall guard hit at sweep {t_chk}\n")
            break

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w") as f:
        f.write("t,mobility,f_ord,n_clusters,r_mean,r_max,n_new,phi_temp,phi_null,wall_s\n")
        for r in rows:
            f.write(",".join(
                (f"{r[0]}", f"{r[1]:.6f}", f"{r[2]:.6f}", f"{r[3]}",
                 f"{r[4]:.4f}", f"{r[5]:.4f}", f"{r[6]}",
                 f"{r[7]:.4f}" if r[7] == r[7] else "nan",
                 f"{r[8]:.4f}" if r[8] == r[8] else "nan",
                 f"{r[9]:.1f}")) + "\n")
    print(f"{mode} L={L} rho={rho} T={T} m={M} sweeps={t_prev} rows={len(rows)} "
          f"wall={time.time()-t_start:.1f}s -> {out_csv}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["glass", "control"], required=True)
    p.add_argument("--L", type=int, default=48)
    p.add_argument("--rho", type=float, default=0.6)
    p.add_argument("--T", type=float, default=0.35)
    p.add_argument("--sweeps", type=int, default=30000)
    p.add_argument("--chk", type=int, default=200)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", required=True)
    p.add_argument("--m", type=int, default=2)
    p.add_argument("--wall-guard", type=float, default=600.0)
    a = p.parse_args()
    run(a.mode, a.L, a.rho, a.T, a.sweeps, a.chk, a.seed, a.out, a.wall_guard, a.m)
