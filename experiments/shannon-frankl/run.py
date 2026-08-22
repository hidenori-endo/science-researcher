#!/usr/bin/env python3
"""Cheap falsification experiment for hypothesis combo:shannon-frankl.

Hypothesis under test: union closure can be modeled as an information-merging
channel, and the Frankl >=1/2 frequency bound follows from a Shannon-style
entropy inequality. Cheap falsification: enumerate / sample real union-closed
families and check candidate entropy inequalities.

Method
------
* n = 4, 5: exhaustive labeled enumeration of union-closed families F with
  U = [n] in F, closed under union (the empty set is optional). Families are
  built by a DFS over subset indices 0..2^n - 1: at each index branch
  "include" (propagating unions with already-included sets as forced future
  memberships) / "skip". Each union-closed family containing U is generated
  exactly once. Node counter + wall-clock caps bound the run.
* n = 6: same DFS under a hard cap (the labeled count is astronomically
  large; partial coverage is lexicographically biased, so n=6 conclusions
  rest mainly on sampling).
* n = 6, 7, 8: randomized sampling: pick k random subsets, close under union
  until stable, force U in, add the empty set w.p. 1/2.
* Control group: random families of matched sizes WITHOUT the closure
  requirement -- does union closure move the entropy statistics at all?

Per-family quantities
---------------------
  m        = |F|
  f_x      = #{S in F : x in S};  p_x = f_x / m   (Bernoulli marginal of a
             uniform random member)
  t        = max_x p_x                              (the Frankl quantity;
             Frankl's conjecture: t >= 1/2 for every nontrivial F)
  q_x      = f_x / sum_y f_y                        (normalized element-
             frequency distribution; sums to 1)
  H(q)     = Shannon entropy of q
  Delta    = sum_x h(p_x) - log2 m                  (coordinate-dependence /
             "merge information"; >= 0 by subadditivity, = 0 iff independent)

Candidate inequalities tested
-----------------------------
  I1  REIMER:        mean_{S in F}|S| >= (1/2) log2 m          (known theorem)
  I2  NAIVE-CEIL:    H(q) <= log2 m - 1                        (naive strawman
                     ceiling; calibration: should FAIL somewhere)
  I3  SHEARER-MERGE: Delta >= 1 ("closure merges at least one bit")
  I4  KNILL:         t >= (m-1)/(2m)                           (known theorem)
  I5  DROPOUT-MONO:  projecting out any element never decreases t
  I6  UNIV-CEILING:  H(q) <= h(max q) + (1 - max q) log2(n-1)  (universal for
                     ANY distribution; sanity check) + measurement of the
                     *slack* of union-closed families below this ceiling,
                     globally and on the boundary class t = 1/2.

Verdict criteria (pre-registered):
  AGAINST       -- some candidate inequality is violated by real union-closed
                   families AND no surviving inequality tightly tracks the
                   1/2 bound (equality structure coinciding with t = 1/2).
  WEAK SUPPORT  -- some inequality holds with equality structure tracking the
                   1/2 bound tightly.
  INCONCLUSIVE  -- otherwise.

Pure stdlib. Usage: python3 run.py [--quick]
"""

from __future__ import annotations

import argparse
import collections
import math
import random
import sys
import time

START = time.time()
BUDGET_SECONDS = 540.0


def elapsed() -> float:
    return time.time() - START


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def shannon(ps) -> float:
    return -sum(p * math.log2(p) for p in ps if p > 0.0)


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def fmt_fam(masks) -> str:
    n = max(masks).bit_length()
    parts = []
    for s in sorted(masks):
        if s == 0:
            parts.append("∅")
        else:
            parts.append("{" + ",".join(str(e) for e in range(n) if (s >> e) & 1) + "}")
    return "{" + ", ".join(parts) + "}"


# ----------------------------------------------------------------------
# exhaustive enumeration (labeled, U forced in)
# ----------------------------------------------------------------------

class BudgetExceeded(Exception):
    pass


def enumerate_union_closed(n: int, node_cap: int, time_cap: float, emit):
    """Call emit(list_of_subset_masks) for every union-closed family on [n]
    containing U. DFS, each family exactly once. Raises BudgetExceeded."""
    full = (1 << n) - 1
    sys.setrecursionlimit(10000 + (1 << n))
    ctx = {"nodes": 0, "t0": time.time()}

    def dfs(i: int, included: int, forced: int):
        ctx["nodes"] += 1
        if ctx["nodes"] > node_cap:
            raise BudgetExceeded
        if ctx["nodes"] % 8192 == 0 and time.time() - ctx["t0"] > time_cap:
            raise BudgetExceeded
        if i > full:
            fam = []
            inc = included
            while inc:
                lb = inc & -inc
                fam.append(lb.bit_length() - 1)
                inc ^= lb
            emit(fam)
            return
        if (forced >> i) & 1:
            options = (1,)
        else:
            options = (0, 1)
        for inc_flag in options:
            if inc_flag == 0:
                dfs(i + 1, included, forced)
                continue
            new_included = included | (1 << i)
            new_forced = forced
            ok = True
            b = included
            while b:
                lb = b & -b
                j = lb.bit_length() - 1
                b ^= lb
                u = i | j
                if u == i or u == j:
                    continue
                if u < i:
                    if not (new_included >> u) & 1:
                        ok = False
                        break
                else:
                    new_forced |= 1 << u
            if ok:
                dfs(i + 1, new_included, new_forced)

    dfs(0, 1 << full, 0)  # force U = full mask in
    return ctx["nodes"]


# ----------------------------------------------------------------------
# per-family statistics + candidate inequality checks
# ----------------------------------------------------------------------

class Agg:
    """Running aggregate over one population of families."""

    def __init__(self, label: str, n: int, keep_examples: int = 4):
        self.label = label
        self.n = n
        self.keep = keep_examples
        self.count = 0
        self.m_max = 0
        self.m_hist = collections.Counter()
        self.t_min = 2.0
        self.t_hist = collections.Counter()          # t rounded to 0.05
        self.hp_sum = 0.0
        self.hp_max = 0.0
        self.delta_sum = 0.0
        self.delta_min = float("inf")
        # candidate inequalities
        self.i1_reimer_viol = 0
        self.i1_min_margin = float("inf")
        self.i2_viol = 0
        self.i2_examples = []
        self.i3_viol = 0
        self.i3_examples = []
        self.i3_min = float("inf")
        self.i4_knill_viol = 0
        self.i5_viol = 0
        self.i5_examples = []
        self.i6_univ_viol = 0
        # boundary class t == 1/2
        self.b_count = 0
        self.b_hp_sum = 0.0
        self.b_hp_max = 0.0
        self.b_delta_sum = 0.0
        self.b_slack_min = float("inf")
        self.b_slack_max = 0.0
        self.b_max_m = 0
        self.b_examples = []

    def add(self, fam_masks) -> None:
        n = self.n
        m = len(fam_masks)
        freq = [0] * n
        size_sum = 0
        for s in fam_masks:
            size_sum += bin(s).count("1")
            x = s
            while x:
                lb = x & -x
                freq[lb.bit_length() - 1] += 1
                x ^= lb
        ps = [f / m for f in freq]
        t = max(ps)
        tot = sum(freq)
        if tot:
            q = [f / tot for f in freq]
        else:  # m == 1, family {∅}? cannot happen (U in F) but guard anyway
            q = [1.0 / n] * n
        hp = shannon(q)
        delta = sum(h2(p) for p in ps) - math.log2(m)
        mean_size = size_sum / m

        self.count += 1
        self.m_max = max(self.m_max, m)
        self.m_hist[m] += 1
        self.t_min = min(self.t_min, t)
        self.t_hist[round(t / 0.05)] += 1
        self.hp_sum += hp
        self.hp_max = max(self.hp_max, hp)
        self.delta_sum += delta
        self.delta_min = min(self.delta_min, delta)

        interesting = False

        # I1 Reimer
        margin = mean_size - 0.5 * math.log2(m)
        self.i1_min_margin = min(self.i1_min_margin, margin)
        if margin < -1e-9:
            self.i1_reimer_viol += 1
            interesting = True
        # I2 naive ceiling
        if hp > math.log2(m) - 1.0 + 1e-9:
            self.i2_viol += 1
            if len(self.i2_examples) < self.keep:
                self.i2_examples.append(tuple(fam_masks))
        # I3 Shearer-merge
        self.i3_min = min(self.i3_min, delta)
        if delta < 1.0 - 1e-9:
            self.i3_viol += 1
            if len(self.i3_examples) < self.keep:
                self.i3_examples.append(tuple(fam_masks))
        # I4 Knill
        if t < (m - 1) / (2.0 * m) - 1e-12:
            self.i4_knill_viol += 1
            interesting = True
        # I5 dropout monotonicity
        for e in range(n):
            proj = {s & ~(1 << e) for s in fam_masks}
            best = 0
            for s in proj:
                c = 0
                x = s
                while x:
                    x &= x - 1
                    c += 1
                if c > best:
                    best = c
            tp = best / len(proj)
            if tp < t - 1e-12:
                self.i5_viol += 1
                if len(self.i5_examples) < self.keep:
                    self.i5_examples.append((tuple(fam_masks), e))
                break
        # I6 universal ceiling (+ boundary class)
        tq = max(q)
        ceil = h2(tq) + (1.0 - tq) * math.log2(n - 1) if n > 1 else 0.0
        if hp > ceil + 1e-9:
            self.i6_univ_viol += 1
            interesting = True
        if abs(t - 0.5) < 1e-9:
            self.b_count += 1
            self.b_hp_sum += hp
            self.b_hp_max = max(self.b_hp_max, hp)
            self.b_delta_sum += delta
            slack = ceil - hp
            self.b_slack_min = min(self.b_slack_min, slack)
            self.b_slack_max = max(self.b_slack_max, slack)
            if m > self.b_max_m:
                self.b_max_m = m
            if len(self.b_examples) < self.keep:
                self.b_examples.append(tuple(fam_masks))

        if interesting and False:  # placeholder: violators recorded above
            pass

    def report(self) -> str:
        n = self.n
        c = max(self.count, 1)
        L = [f"--- population: {self.label} (n={n}) ---"]
        L.append(f"families: {self.count}   max m = {self.m_max}")
        L.append(
            f"t (max freq ratio): min={self.t_min:.4f}   "
            f"H(q): mean={self.hp_sum / c:.4f} max={self.hp_max:.4f}   "
            f"Delta: mean={self.delta_sum / c:.4f} min={self.delta_min:.4f}"
        )
        top_t = sorted(self.t_hist.items())[:4]
        L.append(
            "t histogram (bin=0.05, lowest bins): "
            + ", ".join(f"{k * 0.05:.2f}:{v}" for k, v in top_t)
        )
        L.append(
            f"I1 Reimer     : violations={self.i1_reimer_viol}   "
            f"min margin={self.i1_min_margin:.4f}"
        )
        L.append(f"I2 NAIVE-CEIL : violations={self.i2_viol}")
        for f in self.i2_examples[:2]:
            L.append(f"      e.g. m={len(f)}: {fmt_fam(f)}")
        L.append(
            f"I3 SHEARER-MERGE (Delta>=1): violations={self.i3_viol}   "
            f"min Delta={self.i3_min:.4f}"
        )
        for f in self.i3_examples[:2]:
            L.append(f"      e.g. m={len(f)}: {fmt_fam(f)}")
        L.append(f"I4 Knill      : violations={self.i4_knill_viol}")
        L.append(f"I5 DROPOUT-MONO: violating families={self.i5_viol}")
        for f, e in self.i5_examples[:2]:
            L.append(f"      e.g. drop {e}: {fmt_fam(f)}")
        L.append(f"I6 UNIV-CEILING: violations={self.i6_univ_viol}")
        if self.b_count:
            bc = self.b_count
            L.append(
                "boundary t=1/2: "
                f"count={bc} ({100.0 * bc / c:.3f}%)  "
                f"max H(q)={self.b_hp_max:.4f}  mean H(q)={self.b_hp_sum / bc:.4f}  "
                f"mean Delta={self.b_delta_sum / bc:.4f}  max m={self.b_max_m}"
            )
            L.append(
                f"boundary slack below universal ceiling: "
                f"min={self.b_slack_min:.6f}  max={self.b_slack_max:.6f}"
            )
            for f in self.b_examples[:3]:
                L.append(f"      e.g.: {fmt_fam(f)}")
        else:
            L.append("boundary class t=1/2: EMPTY")
        return "\n".join(L)


# ----------------------------------------------------------------------
# sampling
# ----------------------------------------------------------------------

def random_union_closed(n: int, rng: random.Random):
    N = 1 << n
    k = rng.randint(1, min(N, 2 * n))
    fam = {rng.randrange(N) for _ in range(k)}
    fam.add(N - 1)
    if rng.random() < 0.5:
        fam.add(0)
    changed = True
    while changed:
        changed = False
        cur = list(fam)
        for a in cur:
            for b in cur:
                u = a | b
                if u not in fam:
                    fam.add(u)
                    changed = True
    return sorted(fam)


def run_exhaustive(n: int, node_cap: int, time_cap: float):
    agg = Agg("exhaustive labeled, U in F", n, keep_examples=4)
    complete = True
    try:
        nodes = enumerate_union_closed(
            n, node_cap, time_cap, lambda fam: agg.add(fam)
        )
    except BudgetExceeded:
        complete = False
        nodes = node_cap
    return agg, complete, nodes


def sample_population(n: int, samples: int, seed: int) -> Agg:
    rng = random.Random(seed)
    agg = Agg("random union-closed (sampled)", n)
    for _ in range(samples):
        agg.add(random_union_closed(n, rng))
    return agg


def control_population(n: int, samples: int, m_source: Agg, seed: int) -> Agg:
    rng = random.Random(seed + 1)
    ms = list(m_source.m_hist.elements())
    N = 1 << n
    agg = Agg("random UNCLOSED control (matched m)", n)
    for _ in range(samples):
        m = rng.choice(ms)
        agg.add(rng.sample(range(N), min(m, N)))
    return agg


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smoke-test caps")
    args = ap.parse_args()

    if args.quick:
        caps = [(4, 200_000, 15), (5, 500_000, 30), (6, 300_000, 20)]
        samples = {6: 2000, 7: 1000, 8: 300}
        ctrl = {5: 2000, 6: 1000}
    else:
        caps = [(4, 50_000_000, 60), (5, 80_000_000, 230), (6, 30_000_000, 130)]
        samples = {6: 40_000, 7: 15_000, 8: 4_000}
        ctrl = {5: 20_000, 6: 10_000}

    print(f"# combo:shannon-frankl cheap falsification run "
          f"(overall budget {BUDGET_SECONDS:.0f}s)")

    exhaustive = {}
    for n, node_cap, time_cap in caps:
        if elapsed() > BUDGET_SECONDS:
            print(f"[skip exhaustive n={n}: out of budget]")
            continue
        t0 = time.time()
        agg, complete, nodes = run_exhaustive(n, node_cap, time_cap)
        exhaustive[n] = agg
        status = "COMPLETE" if complete else "CAPPED (partial, lex-biased)"
        print(f"\n[exhaustive n={n}] {status}  nodes={nodes:,}  "
              f"in {time.time() - t0:.1f}s")
        print(agg.report())

    for n in sorted(samples):
        if elapsed() > BUDGET_SECONDS:
            print(f"[skip sampling n={n}: out of budget]")
            continue
        t0 = time.time()
        agg = sample_population(n, samples[n], seed=1000 + n)
        print(f"\n[sampling n={n}] {samples[n]} draws in {time.time() - t0:.1f}s")
        print(agg.report())

    for n in sorted(ctrl):
        src = exhaustive.get(n)
        if src is None or src.count == 0 or elapsed() > BUDGET_SECONDS:
            print(f"[skip control n={n}]")
            continue
        t0 = time.time()
        cagg = control_population(n, ctrl[n], src, seed=2000 + n)
        print(f"\n[control n={n}] {ctrl[n]} draws in {time.time() - t0:.1f}s")
        print(cagg.report())

    print(f"\ntotal wall clock: {elapsed():.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
