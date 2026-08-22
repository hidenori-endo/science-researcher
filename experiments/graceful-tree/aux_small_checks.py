#!/usr/bin/env python3
"""AUXILIARY small-scale checks for THEORY.md (graceful-tree).

NOT the deliverable. These are boundary confirmations of lemmas stated in
THEORY.md, restricted to all free trees with <= 9 vertices (m <= 8 edges).
No search-bound extension is claimed or intended.

Checks:
  A. Parity invariant  sum_v deg(v) f(v) == m(m+1)/2 (mod 2) on every
     graceful labeling (Lemma P in THEORY.md).
  B. Extension rigidity: fraction of graceful labelings of T - l
     (labels {0..m-1}) whose parent-of-leaf vertex sits at label 0,
     i.e. the ONLY extendable position (Lemma L1).
  C. VTE-strong: for every tree and EVERY vertex v there is a graceful
     labeling with f(v) = 0 (statement VTE in THEORY.md; true here, but
     not reachable by the leaf-induction -- see L5).
  D. Slack-1 flexibility: injection into {0..m+1} with edge diffs exactly
     {1..m} and prescribed vertex at 0 (the sigma = 1 instance that the
     avoidance-carrying induction targets; see L5).
  E. Same as C/D stratified by number of branching vertices (deg >= 3),
     to locate the caterpillar/frontier line empirically.
"""
import itertools
from collections import defaultdict
from networkx.generators.nonisomorphic_trees import nonisomorphic_trees


def graceful_labelings(n_vertices, edges, M, allowed_diffs):
    """All injective f: V -> {0..M} with every edge diff in allowed_diffs."""
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    # BFS order from vertex 0 for tight pruning
    order, seen = [0], {0}
    while len(order) < n_vertices:
        for x in order:
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    order.append(y)
    m = len(edges)
    lab, used, diffs = {}, set(), set()
    out = []

    def bt(i):
        if i == n_vertices:
            out.append(dict(lab))
            return
        v = order[i]
        for L in range(M + 1):
            if L in used:
                continue
            added = []
            ok = True
            for u in adj[v]:
                if u in lab:
                    d = abs(L - lab[u])
                    if d not in allowed_diffs or d in diffs:
                        ok = False
                        break
                    added.append((d, u))
            if ok:
                lab[v] = L
                used.add(L)
                diffs.update(d for d, _ in added)
                bt(i + 1)
                diffs.difference_update(d for d, _ in added)
                used.discard(L)
                del lab[v]

    bt(0)
    return out


def full_graceful(n, edges):
    m = len(edges)
    return graceful_labelings(n, edges, M=m, allowed_diffs=set(range(1, m + 1)))


def leaves_and_parents(edges, n):
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    out = []
    for l in range(n):
        if len(adj[l]) == 1:
            out.append((l, adj[l][0]))
    return out


def strip_leaf(edges, leaf, n):
    return [(u, v) for u, v in edges if u != leaf and v != leaf]


def renumber(edges, keep):
    idx = {v: i for i, v in enumerate(sorted(keep))}
    return [(idx[u], idx[v]) for u, v in edges], idx


def branching_count(edges, n):
    adj = defaultdict(int)
    for u, v in edges:
        adj[u] += 1
        adj[v] += 1
    return sum(1 for v in range(n) if adj[v] >= 3)


def main():
    print("=" * 72)
    print("AUXILIARY CHECKS -- all free trees with <= 9 vertices (m <= 8)")
    print("=" * 72)

    fail_parity = fail_vte = fail_slack1 = 0
    ext_fracs = []
    strat = defaultdict(lambda: {"vte_ok": 0, "slack_ok": 0, "n": 0})

    for n in range(2, 10):
        m = n - 1
        for nx_tree in nonisomorphic_trees(n):
            edges = sorted(nx_tree.edges())
            G = full_graceful(n, edges)

            # A: parity invariant on every graceful labeling
            target = (m * (m + 1) // 2) % 2
            deg = defaultdict(int)
            for u, v in edges:
                deg[u] += 1
                deg[v] += 1
            for f in G:
                if sum(deg[v] * f[v] for v in range(n)) % 2 != target:
                    fail_parity += 1

            # B: extension rigidity density (parent at 0 among T-leaf labelings)
            for leaf, par in leaves_and_parents(edges, n):
                e2, idx = renumber(strip_leaf(edges, leaf, n), set(range(n)) - {leaf})
                inv_par = idx[par]
                G2 = full_graceful(n - 1, e2)
                if G2:
                    frac = sum(1 for f in G2 if f[inv_par] == 0) / len(G2)
                    ext_fracs.append(((n, m), frac))

            # C: VTE-strong (every vertex can sit at 0)
            vte_ok = True
            for v in range(n):
                if not any(f[v] == 0 for f in G):
                    vte_ok = False
            # D: slack-1, prescribed vertex at 0, diffs exactly {1..m}
            slack_ok = True
            S1 = set(range(1, m + 1))
            for v in range(n):
                labs = graceful_labelings(n, edges, M=m + 1, allowed_diffs=S1)
                if not any(f[v] == 0 for f in labs):
                    slack_ok = False
            b = branching_count(edges, n)
            strat[b]["n"] += 1
            strat[b]["vte_ok"] += vte_ok
            strat[b]["slack_ok"] += slack_ok
            if not vte_ok:
                fail_vte += 1
                print(f"VTE FAIL: n={n} edges={sorted(edges)}")
            if not slack_ok:
                fail_slack1 += 1
                print(f"SLACK-1 FAIL: n={n} edges={sorted(edges)}")

    tot_lab_check = fail_parity == 0
    print(f"\n[A] Parity invariant violated in {fail_parity} labelings "
          f"(expect 0).  Invariant holds: {tot_lab_check}")
    if ext_fracs:
        fr = [f for _, f in ext_fracs]
        mx = max(fr)
        nz = [f for f in fr if f > 0]
        print(f"[B] Extension-rigidity density over {len(fr)} (tree, leaf) pairs:")
        print(f"    max fraction of T'--graceful labelings with parent at 0 "
              f"(extendable): {mx:.4f}")
        print(f"    pairs with ANY extendable labeling: {len(nz)}/{len(fr)}")
        print(f"    mean fraction over all pairs: {sum(fr)/len(fr):.4f}")
        worst = max(ext_fracs, key=lambda t: t[1])
        print(f"    max occurs at n={worst[0][0]} (m={worst[0][1]}), frac={worst[1]:.4f}")
    print(f"[C] VTE-strong failures: {fail_vte} trees (expect 0 if true up to n=9)")
    print(f"[D] Slack-1 ({'diffs {1..m} into {0..m+1}, v at 0'}) failures: "
          f"{fail_slack1} trees")
    print("[E] Stratified by #branching vertices (deg>=3):")
    print(f"    {'#branch':>8} {'trees':>6} {'VTE-ok':>7} {'slack1-ok':>10}")
    for b in sorted(strat):
        s = strat[b]
        print(f"    {b:>8} {s['n']:>6} {s['vte_ok']:>7} {s['slack_ok']:>10}")


if __name__ == "__main__":
    main()
