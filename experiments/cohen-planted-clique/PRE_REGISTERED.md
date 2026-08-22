# Pre-registration — experiments/cohen-planted-clique

Claim: `combo:cohen-planted-clique` (Cohen-style forcing construction for planted
clique thresholds). Written **before** running any measurement. The code
(`experiment.py`) is written to implement exactly this protocol; results and the
verdict go to `RESULTS.md` afterwards, with no post-hoc change to the criteria.

## Question

Can we engineer two random-graph worlds at the same planted size k whose simple
global statistics are statistically indistinguishable, while one contains a
planted k-clique ("loud truth") and the other a planted independent set of size
k ("quiet truth")? If yes and some implemented detector separates them, the
constructive (forcing-style) program demonstrates method-relativity of the
detection threshold at this scale; if no detector separates them under matched
statistics, the constructive program stalls at this scale.

## Scale choice (justified deviation from k ≈ log2(n)^2)

n = 1000. log2(n)^2 ≈ 99.7, but sqrt(n) ≈ 31.6 > 2·log2(n) ≈ 19.9.

- At k = 100 (> sqrt(n)), EVERY generic detector trivially finds any planted
  clique in any world containing one; "same k, different worlds" would be
  decided by construction artifacts, not by algorithmic content.
- We therefore use **k = 20 ≈ 2·log2(n)**, the information-theoretic threshold,
  inside the conjectured-hard band (k < sqrt(n)). This is the regime where
  forcing-style world construction has real work to do.

## Worlds (m = 20 independent draws each)

- `W_null`  : G(n, 1/2).
- `W_clique`: G(n, 1/2) ∪ K_k on a uniformly random k-set C. Contains a K_20 by
  construction.
- `W_quiet` : G(n, 1/2); pick uniform k-set Q; delete all intra-Q edges (Q
  becomes an independent set); re-add the same number of edges as uniform
  non-edges with BOTH endpoints outside Q. Contains an independent set of size
  20 by construction; total edge count preserved exactly.

RNG: Python `random.Random`, seeded per draw (`world-trial` string), fixed
beforehand. n=1000, k=20, m=20 per world (60 graphs).

## Operational definition of "indistinguishable"

Matched statistics (computed on every graph):

- S1: mean degree
- S2: standard deviation of the degree sequence
- S3: maximum degree
- S4: triangle count

**Pass condition:** for each Sj, a two-sided permutation test (20,000 shuffles)
between W_clique and W_quiet must NOT reject at α = 0.05, i.e. p_match(Sj) ≥ 0.05
for all four statistics. Worlds are "indistinguishable" iff all four pass.
If any statistic fails to match, the construction itself failed → verdict is
INCONCLUSIVE regardless of detector outcomes.

## Detectors

- D1 greedy: start at max-degree vertex; repeatedly add the candidate neighbor
  maximizing its degree inside the current candidate set. Score = final clique
  size.
- D2 spectral: power iteration on the adjacency matrix (Perron vector), byte-
  quantized lanes for pure-Python speed, 40 iterations, init proportional to
  degree. Primary score = localization (peak-to-mean of the Perron vector);
  secondary = Rayleigh quotient (λ1 estimate). Each tested separately with
  Bonferroni α = 0.005.
- D3 combinatorial branch-and-bound clique search with pruning (prune when
  |current| + |candidates| cannot beat best or reach k), candidates ordered by
  common-neighbor count descending, global node budget 150,000 expansions per
  graph, early stop at size ≥ k. Score = largest clique found.

## Separation criterion (per detector)

Permutation test (20,000 shuffles) on the detector score between W_clique and
W_quiet. "Detector d separates the worlds" iff:
- D1/D3: one-sided p < 0.01 AND mean(W_clique) > mean(W_quiet);
- D2: two-sided p < α_d (α_localization = 0.005, α_λ1 = 0.005) AND the sign of
  the difference agrees across all m paired draws' direction test... simplified:
  sign(mean_clique − mean_quiet) ≠ 0 and consistent with theory (clique world
  more localized / higher λ1).

Context (not part of verdict): each detector also tested W_clique vs W_null and
W_quiet vs W_null.

## Verdict rules (fixed now)

- Statistics all match (S1–S4) AND ≥ 1 detector separates →
  **SUPPORT** (upgrade path: the constructive program realizes different
  algorithmic truths at the same k under matched observables). SUPPORT only
  upgrades the stage; it does not resolve the claim.
- Statistics all match AND 0 detectors separate →
  **AGAINST** (at this scale): closeness forced identical detector behavior;
  constructive program stalls early, matching the card's stated failure mode.
- Any statistic fails to match, or results are internally inconsistent →
  **INCONCLUSIVE**.

## Implementation amendments (dated, before the official m=20 run)

Smoke tests on single graphs (run before any W_clique-vs-W_quiet comparison)
exposed three implementation bugs plus one design flaw, all fixed BEFORE the
official run. Scoring definitions and all pass/fail criteria above are
unchanged.

1. Triangle count double-counted ordered edges (divided by 3 instead of 6) and
   skipped the last row; fixed and verified against brute force on small
   graphs. Note: the empirical std of G(1000,1/2) triangle counts is ~n²-scale
   (~90k), much larger than the independent-edge binomial estimate; this only
   affects intuition, not the permutation tests.
2. D3 branch-and-bound never updated its `best` variable; fixed.
3. D2's quantized matvec bitwise-ANDed a vertex-index mask with an incompatible
   lane-packed weight vector, returning garbage (lambda estimate 62 instead of
   ~500). Replaced with a faithful power iteration whose float matvec is
   computed via 64-block decomposition and 4-bit weight masks with C-speed
   int.bit_count(); verified against a float reference power iteration on a
   small graph (lambda 19.385 vs 19.400).
4. Diagnostic observation (both worlds equally, no cross-world comparison done):
   vertex-rooted B&B with the registered 150k-node budget saturates at the
   BACKGROUND clique number of G(1000,1/2) (~14, matching 2 log2 n - 2 log2
   log2 n) rather than finding any planted K_20. Budget stays as registered;
   an offline robustness probe with larger budgets will be reported separately
   as a diagnostic, not used for the verdict.

## Compute budget

Pure Python stdlib only. Wall-clock cap 40 minutes; elapsed time measured and
reported. If the cap is hit, partial data is reported and the verdict is
INCONCLUSIVE unless already decidable from completed runs.

## Honest limitations (declared in advance)

3 weak detectors (no SDP), single scale (n=1000, k=20), m=20 draws, permutation
tests at generous α. This experiment cannot settle average-case complexity; it
only tests whether the forcing-style construction is even off the ground at a
small scale.
