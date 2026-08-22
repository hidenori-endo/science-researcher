# RESULTS — combo:shannon-frankl cheap falsification

**Hypothesis.** Frankl's union-closed conjecture attacked Shannon-style: model union
closure as an information-merging channel and prove the ≥1/2 frequency bound as a
consequence of an entropy inequality. Cheap falsification: search computationally for
union-closed families violating candidate entropy inequalities; if the natural
inequality routes die quickly, downgrade.

**Verdict: AGAINST** (see Verdict section).

Reproduce: `python3 experiments/shannon-frankl/run.py` (≈6.2 min; `--quick` for a
~40 s smoke test). Pure Python stdlib, fixed seeds, deterministic.

## Method

*Representation.* Ground set [n]; subsets are bitmasks 0..2ⁿ−1. A family is
union-closed, contains U=[n] (normalization; the empty set is optional), and is
enumerated by DFS over subset indices with forced-union propagation — each family is
generated exactly once.

*Populations* (run of 2026-02-27, total wall clock 373.9 s, budget 540 s):

| population | coverage | families | notes |
|---|---|---|---|
| exhaustive n=4 | **COMPLETE** (17,635 DFS nodes, 0.3 s) | 4,960 | |
| exhaustive n=5 | CAPPED at 80M nodes / 230 s | 2,288,416 | partial, lexicographically biased |
| exhaustive n=6 | CAPPED at 30M nodes / 130 s | 1,219,796 | partial, lex-biased (all in the t=1.0 corner; excluded from conclusions) |
| sampled n=6 | 40,000 random closure systems | 40,000 | random seeds → union-close to stability, U forced, ∅ w.p. ½ |
| sampled n=7 | 15,000 draws | 15,000 | |
| sampled n=8 | 4,000 draws | 4,000 | |
| control n=5 | 20,000 random **unclosed** families, m matched to the n=5 histogram | 20,000 | does closure move the entropy stats at all? |
| control n=6 | 10,000 unclosed, m matched | 10,000 | |

*Per-family quantities.* m=|F|; f_x = frequency of element x; p_x = f_x/m (Bernoulli
marginal of a uniform random member); **t = max_x p_x** (the Frankl quantity);
q_x = f_x/Σ_y f_y (normalized element-frequency distribution); H(q) = Shannon entropy
of q; Δ = Σ_x h(p_x) − log₂ m (coordinate dependence / "merge information"; ≥ 0 by
subadditivity, = 0 iff the membership bits are independent).

## Inequalities tested and outcomes

| id | candidate | statement | violations observed | status |
|---|---|---|---|---|
| I1 | Reimer | mean\|S\| ≥ ½·log₂ m | **0** (min margin 0.0000 at n=4 — equality at the powerset; 0.1035 on capped n=5; 0.2381 sampled n=6) | holds (known theorem); does **not** logically imply Frankl |
| I2 | naive entropy ceiling | H(q) ≤ log₂ m − 1 | 2,589/4,960 (n=4); 187,738 (n=5); 17,938/40,000 (n=6 sampled); e.g. F={U}, F={∅,U}, F={S,U} | **FALSE** on real union-closed families (strawman calibration: naive ceilings die immediately) |
| I3 | Shearer-merge | Δ ≥ 1 ("closure merges ≥ 1 bit") | 4,019/4,960 (n=4); 7,119/40,000 (n=6 sampled); counterexample F={S,U}: p_S=½, rest 1 → Δ = 0; also powersets (Δ=0) | **FALSE** — the natural "one bit of merging" formalization is dead |
| I4 | Knill | t ≥ (m−1)/(2m) | **0** everywhere | holds (known theorem); strictly weaker than Frankl |
| I5 | dropout monotonicity | projecting out any element never decreases t | 4,550/4,960 (n=4); 29,707/40,000 (n=6 sampled); e.g. {23,023,123,0123}: t=1 → drop 2 → t=½… (many worse) | **FALSE** — projection does not interact monotonicity with the Frankl quantity |
| I6 | universal entropy ceiling | H(q) ≤ h(max q) + (1−max q)·log₂(n−1) | **0** in every population (sanity check — this holds for *all* distributions, not just union-closed) | holds vacuously w.r.t. closure; **slack is exactly 0 at the Frankl boundary** |

## Key numbers

1. **Frankl itself: no counterexample anywhere.** min t = 0.5000 in the complete n=4
   enumeration, both sampled n=6/7/8 populations, and every control-free population.
   The boundary class t = 1/2 is nonempty but thin: 16/4,960 = 0.32% (n=4),
   141/40,000 = 0.35% (n=6 sampled), 12/15,000 = 0.08% (n=7), 1/4,000 (n=8).
2. **The surviving ceiling saturates at the boundary.** On the t=1/2 class, the slack
   below the universal ceiling I6 is exactly 0 (min = max = 0 in n=4, n=5, and all
   sampled populations): families like {∅,U} (uniform q) sit *on* the ceiling. Any
   ceiling-type entropy inequality valid for all union-closed families therefore
   **cannot be strengthened to exclude t < 1/2** — the ceiling route provably
   saturates at the Frankl bound and can never cross it.
3. **Entropy statistics do not carry the closure signature.** Union-closed vs matched
   unclosed control at n=5: mean H(q) 2.2886 vs 2.2948 (max identical 2.3219); mean Δ
   0.767 vs 1.024. The only statistic that cleanly separates closed from unclosed is
   t itself (control min t = 0.364, 6.5% of controls below 0.5) — i.e., the "channel"
   statistics add nothing beyond restating Frankl.
4. **Known theorems confirmed as sanity anchors:** Reimer (I1) and Knill (I4) with
   zero violations across ~3.6M families; Reimer's margin reaches 0 at the powerset,
   which is also Frankl-tight (t=1/2) — tightness of I1 coincides with the boundary
   but the implication I1 ⇒ Frankl is false in general.

## Verdict: AGAINST

By the pre-registered criteria:

* Several candidate formalizations of "an entropy inequality implied by union
  closure" are **violated by real union-closed families** (I2, I3, I5) — they die
  immediately and cheaply, exactly the failure mode the hypothesis's own
  falsification test anticipated.
* The inequalities that *do* survive are (a) known theorems (Reimer, Knill) that
  provably do not imply the 1/2 bound, or (b) the distribution-universal ceiling
  (I6), which union closure **saturates with equality exactly at t = 1/2** — so no
  ceiling-style inequality can be pushed past the Frankl boundary.
* The control experiment shows the Shannon-style statistics (H(q), Δ) barely
  distinguish union-closed from generic families; the discriminat signal is t alone.

This is evidence against the *ceiling/typicality* version of the Shannon attack. The
hypothesis should be downgraded per its own cheap-falsification clause. (Caveats: n=5
exhaustive coverage is partial and n=6 exhaustive is lexicographically biased — the
AGAINST verdict rests on the complete n=4 enumeration, 59k unbiased samples at
n=6–8, and the analytic saturation argument in Key number 2, none of which depend on
the capped runs.)

## Next-step suggestion

The one quantity where closure left a measurable fingerprint is **Δ** (mean 0.767
closed vs 1.024 matched-unclosed at n=5 — closure makes the membership coordinates
*more* independent, which is the opposite of the "merging channel" picture). If any
Shannon-style route is worth one more look, it is a *minimum-Δ characterization*:
study whether min-Δ union-closed families at fixed (n, m) always have t ≥ 1/2 with
equality structure (powersets, {∅,U} chains suggest so). Otherwise, redirect effort
to combinatorial routes (e.g., the Balla–Bollobás–Eccles separating-family
reduction), which this experiment indirectly favors.
