# Pre-registered criteria — experiments/galois-edit

Written **before** running any computation (before DP distances or sketch
statistics were computed for the corpus below). Timestamped by the session;
the corpus generator seeds are fixed here in advance.

## Target claim

`combo:galois-edit-distance` — prove the quadratic edit-distance barrier
structurally via a Galois-style invariant that any strongly subquadratic
edit-distance algorithm would have to respect. This experiment probes
whether any *cheaply computable* invariant (a stand-in for "what an
o(n²)-time algorithm can afford to read") carries enough information about
edit distance to be a live obstruction candidate.

## Candidate invariants (formalized before probing)

Let x, y ∈ Σ^n, ED(x,y) = Levenshtein distance, n = |x|.

- **C1 (histogram invariant).** Statistic H(x,y) = ½·L1(c_x − c_y), where
  c_s(a) = #occurrences of a in s. Conjecture C1: H is a usable
  distance certificate (predicts ED up to a constant factor on all pairs).
  *Known formal counterexample to be verified numerically:* x = 0^{n/2}1^{n/2},
  y = 1^{n/2}0^{n/2} has H = 0 but ED = n (rotation ⇒ delete+insert n chars;
  substitution count is also n... recorded from computation, prediction
  written in advance: ED ≥ n/2 by mismatch count under either metric).

- **C2 (q-gram lower bound).** For q-gram multiset counts g_s(w), let
  M = Σ_w min(g_x(w), g_y(w)) (shared mass), N_s = n − q + 1. Known lemma:
  ED(x,y) ≥ (N_x + N_y − M)/(q+1) ≡ LB_q. Conjecture C2: LB_q is a usable
  certificate (tight up to a small constant factor).

- **C3 (sublinear-read information invariant).** An algorithm that reads
  r positions per string (contiguous windows of length w = 3, at r/3 random
  start offsets) sees a sketch. Conjecture C3 (barrier form): the sketch
  carries enough information to predict ED within useful accuracy only when
  r = Ω(n); its computational proxy: prediction quality as a function of
  read budget r ∈ {⌈0.01n⌉, ⌈0.05n⌉, ⌈0.25n⌉}. Features from the sketch:
  per-symbol frequency differences, fraction of matching sampled indices,
  count of matching sampled 3-gram windows. Predictor: ridge regression
  (closed form, pure stdlib) + a threshold classifier for near/far.

## Corpus (fixed in advance, seeded RNG)

All pairs n = 1000 unless noted; seeds = Python `random.Random(seed)`:

1. `rand4` — 40 pairs, uniform random over Σ = {0,1,2,3}, seeds 1000–1039.
2. `rand2` — 20 pairs, uniform random binary, seeds 2000–2019.
3. `planted` — 30 pairs, x random4, y = x with k random edits
   (sub/ins/del each 1/3), k/n ∈ {0.02, 0.05, 0.10, 0.20, 0.30}, 6 seeds
   each (3000–3029). Ground truth ED computed by DP.
4. `perm` — 30 pairs, x random balanced binary, y a permutation of x
   (identical histograms): (a) 10 full random shuffles, (b) 10 block swaps
   of a random block boundary, (c) 10 with t ∈ {1,2,4,8,16,32,64,128,256,512}
   random adjacent transpositions (seeds 4000–4029).
5. `adv` — 6 adversarial pairs designed to fool sampled-agreement:
   x = 0^n vs y = 0^{n/2}1^{n/2}; x = 0^n vs y = (01)^{n/2};
   x = 0^{n/2}1^{n/2} vs y = 1^{n/2}0^{n/2}; plus 3 random4 pairs as
   controls (seeds 5000–5005).
6. `scale` — 10 pairs at n = 2000 (5 random4, 5 perm-full-shuffle),
   seeds 6000–6009, for a runtime/scaling note only (not in fit corpora).

Total: 136 DP instances (n = 1000) + 10 (n = 2000).

## Pre-registered pass/fail criteria

An invariant is **USABLE** on a corpus if it meets BOTH:

- Spearman rank correlation ρ(statistic, ED) ≥ 0.90 on the corpus, AND
- worst-case relative prediction error ≤ 3× using the best monotone fit of
  ED on the statistic (fit on `rand4`+`planted`, evaluated worst-case on
  the full corpus including `perm`, `adv`).

Per-conjecture outcomes:

- **C1** — expected to be NOT usable (formal counterexample above).
  Pass-through criterion (supports barrier narrative): exists a corpus pair
  with H = 0 and ED ≥ n/4.
- **C2** — usable if median ED/LB_5 ≤ 3 and ρ(LB_5, ED) ≥ 0.90 over the
  full n=1000 corpus; additionally report the ratio distribution on `perm`.
- **C3** — "information suffices" if near/far classification error
  (near: ED ≤ 0.1n, far: ED ≥ 0.4n) ≤ 10% at read budget r = 0.05n on the
  random+planted corpus. Barrier-live if error > 20% at r = 0.25n on the
  same corpus. `adv` pairs are reported separately as a formal-fooling
  check, not folded into the fit.

## Overall verdict rule (fixed now)

- **INCONCLUSIVE leaning SUPPORT**: ≥ 1 invariant is USABLE on the full
  corpus (random AND structured) — i.e., a live nontrivial certificate
  exists that o(n)-read algorithms could exploit.
- **AGAINST (downgrade)**: no invariant is USABLE on any non-toy corpus,
  AND each formalization is judged (in RESULTS.md, case by case) to
  collapse to a known statement (folklore counterexample / known lemma /
  property-testing result) rather than new structure.
- **Otherwise**: INCONCLUSIVE, with the lean and reasons documented.

## Runtime cap

Hard cap 35 minutes wall clock for the full run; elapsed time is recorded
in results.json and reported in RESULTS.md.
