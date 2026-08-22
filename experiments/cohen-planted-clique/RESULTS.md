# RESULTS — combo:cohen-planted-clique (forcing-style world construction)

Experiment: two random-graph worlds at n=1000 with opposite planted ground
truths at the same k, matched on pre-registered statistics; measure whether any
implemented detector tells them apart.

**Verdict: AGAINST (at this scale)** — per the pre-registered rule
("statistics all match AND 0 detectors separate").

## Method

Full protocol in `PRE_REGISTERED.md` (written before the run; includes a dated
implementation-amendment section for bugs found and fixed during smoke tests,
before any cross-world comparison). Summary:

- n = 1000, k = 20 ≈ 2·log2(n). The task suggested k ≈ log2(n)² ≈ 100, but
  sqrt(n) ≈ 31.6 < 100: at k = 100 every generic detector trivially finds any
  planted clique, making "same k, different worlds" decided by construction
  artifacts. k = 20 sits at the information-theoretic threshold, inside the
  conjectured-hard band k < sqrt(n), where forcing-style construction has real
  work to do. This deviation is justified, pre-registered, and itself part of
  the finding (see Caveats).
- Worlds, m = 20 draws each (fixed RNG seeds):
  - `W_null`: G(n, 1/2).
  - `W_clique`: G(n, 1/2) ∪ K₂₀ on a random 20-set (unique K₂₀ by construction).
  - `W_quiet`: G(n, 1/2); a random 20-set Q made independent; the deleted
    intra-Q edges re-added as uniform random non-edges outside Q. Same edge
    count exactly; Q is an independent 20-set (a "quiet" structure invisible to
    clique-seeking algorithms).
- Matched statistics (operational "indistinguishable"): mean degree, degree
  std, max degree, triangle count; two-sided permutation test (20k shuffles),
  all four must have p ≥ 0.05.
- Detectors: D1 greedy clique heuristic; D2 spectral power iteration (true
  Perron iteration; float matvec via 64-block / 4-bit weight-mask decomposition
  with `int.bit_count()`, verified against a float reference: λ 19.385 vs
  19.400 on a check graph); D3 branch-and-bound clique search with pruning,
  150k-node budget, early stop at size 20.
- All comparisons: permutation tests (20k shuffles). Separation at α = 0.01
  (D1, D3, one-sided) / α = 0.005 (D2, two-sided, two scores).
- Pure Python stdlib; official run 411.6 s wall clock (well under the 40-min
  cap), plus ~180 s of pre-declared robustness probes reported below.

## Pre-registered pass/fail criteria (verbatim summary)

- Indistinguishable ⟺ all four statistics: two-sided permutation p ≥ 0.05
  between W_clique and W_quiet.
- Detector separates ⟺ significant score difference in the clique-favoring
  direction between W_clique and W_quiet.
- Verdict: stats matched + ≥1 separation → SUPPORT (upgrade path); stats
  matched + 0 separations → AGAINST (at this scale); any stat unmatched →
  INCONCLUSIVE.

## Numbers

Statistics matching, W_clique vs W_quiet (all matched):

| statistic  | mean (clique) | mean (quiet) | p (two-sided) |
|-----------:|--------------:|-------------:|--------------:|
| mean deg   | 499.427       | 499.527      | 0.575         |
| std deg    | 15.893        | 15.769       | 0.315         |
| max deg    | 553.0         | 552.55       | 0.863         |
| triangles  | 20,763,171    | 20,773,357   | 0.648         |

Detector separation, W_clique vs W_quiet (primary comparison; **none
separate**):

| detector              | mean (clique) | mean (quiet) | delta  | p      | separates |
|-----------------------|--------------:|-------------:|-------:|-------:|-----------|
| D1 greedy (clique sz) | 12.50         | 12.35        | +0.15  | 0.330  | no        |
| D3 B&B (clique sz)    | 13.50         | 13.90        | −0.40  | 0.998  | no        |
| D2 λ1                 | 499.72        | 499.81       | −0.09  | 0.614  | no        |
| D2 localization       | 1.0683        | 1.0669       | +0.001 | 0.732  | no        |

Context, W_clique vs W_null (the "loud" world is also invisible against pure
noise): greedy p=0.174, B&B p=0.506, λ1 p=0.725, localization p=0.079 — none
significant.

Detector saturation levels (all worlds): greedy ≈ 12.3–12.5, B&B ≈ 13.5–13.9,
λ1 ≈ 499.7–499.8, localization ≈ 1.062–1.068. The B&B and greedy scores sit at
the BACKGROUND clique number of G(1000, 1/2) (≈ 2 log2 n − 2 log2 log2 n ≈ 14):
both algorithms return essentially the same quantity on all three worlds, and
that quantity is a property of the null, not of the planting.

Robustness probe (pre-declared diagnostic, not used for the verdict): raising
the B&B budget 33× to 5,000,000 nodes (~84 s/graph) still finds nothing above
background: best clique = 14 on a W_clique draw, 15 on a W_quiet draw. The
planted K₂₀ is not within reach of budget scaling of this search.

Multiplicity note: across the 12 reported pairwise tests, one nominal p = 0.012
(B&B, W_quiet vs W_null, direction *opposite* to a clique signal) appears; it
does not survive any multiplicity correction and is consistent with noise.

## Verdict

**AGAINST (at this scale).** The engineered worlds satisfy the registered
indistinguishability criteria on all four statistics while carrying opposite
planted ground truths (unique K₂₀ vs independent 20-set), and **no implemented
detector separates them** — indeed nothing separates W_clique from W_null. At
this scale, statistical closeness forced identical algorithmic outcomes across
worlds, which is precisely the card's declared failure mode for the
constructive program ("indistinguishability between engineered worlds may
collapse …; nothing beyond known bounds"). Per the guidance, this is recorded
honestly as evidence against the constructive program at this scale.

## Honest caveats

1. **AGAINST is detector-relative.** The ground truths genuinely differ: a
   unique K₂₀ exists in every W_clique draw by construction, so an exhaustive
   (astronomically expensive) search separates the worlds. What failed is
   feasible detection: three weak detector families (greedy, first-order
   spectral, budget-limited B&B). No SDP/SoS relaxation, no common-neighborhood
   second-order statistics, no color-coding/algebraic fingerprinting was run.
   The result is "the constructive program currently has no observable leverage
   over feasible algorithms at this scale", not "no algorithm can tell the
   worlds apart".
2. **k = 20 is below every known polynomial detection threshold** (k ≳ √n for
   spectral/SDP). That is why the scale was chosen — but it means the AGAINST
   partially restates known planted-clique hardness as a construction failure.
   The registered alternative (k ≈ log²n = 100 > √n) would have produced a
   vacuous SUPPORT: every world containing a planted K₁₀₀ is trivially loud.
3. **Power is limited**: m = 20 draws per world; observed deltas are tiny and
   even sign-inconsistent across detectors, so a real but small effect is
   unlikely — but a modest effect cannot be excluded.
4. **One quiet construction was tried.** Other "generic" quiet rewires might
   leak on the matched statistics (the triangle balance of the rewire is only
   neutral in expectation, ±~10³ triangles against an empirical σ ≈ 9·10⁴).
5. **Matched statistics are first-order.** The worlds differ violently in
   higher-order statistics (e.g., the number of K₂₀'s: 1 vs ~0). The forcing
   program's actual target — matching all poly-time-testable statistics — is
   far beyond what this experiment can construct or test.

## Next step

Before re-testing the construction, upgrade the detector class, because the
current AGAINST is bounded by detector weakness, not by the construction:

1. Add a second-order detector (top eigenvector of the common-neighborhood /
   A∘A matrix) and a small SDP-style vector relaxation at reduced n (e.g.,
   n = 400) where pure Python is still feasible; re-run the same two-world
   protocol. Separation by a stronger detector under matched first-order
   statistics would upgrade the claim to SUPPORT (stage 2: method-relativity
   demonstrated constructively).
2. Map the leverage point: fix the construction and scan k = 20 → 32 at n =
   1000 to find the empirical k* where any detector's separation switches on;
   the location of k* relative to √n is the constructive content of the
   forcing program at this scale.

## Artifacts

- `PRE_REGISTERED.md` — protocol, criteria, dated amendments (pre-run)
- `experiment.py` — runnable, stdlib-only, `python3 experiment.py` (~7 min)
- `results.json` — full per-graph records, all test statistics, verdict
