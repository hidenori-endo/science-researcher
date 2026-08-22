# RESULTS — experiments/galois-edit

Claim: `combo:galois-edit-distance` — prove the quadratic edit-distance
barrier structurally via a Galois-style invariant that any strongly
subquadratic algorithm would have to respect.

**Verdict: INCONCLUSIVE, leaning AGAINST.**
No probed invariant survives adversarial structure; none of the three
formalizations produced new structure, but not all of them collapsed
cleanly to known statements either, so the pre-registered bar for AGAINST
(downgrade) is not fully met.

Runtime: 110 s wall clock (cap 35 min), pure Python stdlib, 136 exact-DP
pairs (124 at n = 1000, 10 at n = 2000, plus 2 adv). All numbers below are
from this session's run (`results.json`); criteria were fixed in
`PREREGISTER.md` before any computation.

## Method

For each corpus pair we computed the exact Levenshtein distance (two-row
DP), three candidate invariant statistics, and sublinear-read sketches:

- **C1 histogram statistic** H = ½·L1 of symbol-count vectors.
- **C2 q-gram lower bound** LB_5 (Ukkonen-type; see deviation note below).
- **C3 sampled-read sketch**: r ∈ {10, 50, 250} positions/string read at
  uniform random offsets (5 repetitions averaged), yielding a fixed
  6-feature vector (per-symbol frequency differences, matched-index
  fraction, matched-window fraction). Prediction: closed-form ridge
  regression trained on `rand4`+`planted`, evaluated on all n=1000 pairs;
  near/far classification (near: ED ≤ 0.1n, far: ED ≥ 0.4n) by thresholding
  the prediction at 0.25n.

Corpus (all seeded in advance): 40 random quaternary pairs, 20 random
binary, 30 planted-edit pairs (edit rate 2–30%), 30 permutation pairs with
identical histograms (full shuffle / block swap / t adjacent
transpositions), 6 adversarial pairs, 10 scaling pairs at n = 2000.

## Pre-registered deviations (both are corrections, thresholds unchanged)

1. The pre-registered C2 formula ED ≥ (N_x+N_y−M)/(q+1) (M = multiset
   intersection mass) is **not a valid lower bound** — our own corpus
   falsified it before analysis (identical strings give LB > 0). It was
   replaced by the standard Ukkonen-type bound
   e ≥ max((N_x−M)/q, (N_y−M)/q), which we verified analytically (each
   edit changes x's q-gram multiset by ≤ q insertions and ≤ q deletions)
   and numerically (LB ≤ ED asserted on all 136 pairs + 200 random unit
   trials; LB(x,x) = 0).
2. One corpus pair (perm-trans seed 4020) turned out to have ED = 0
   (transposition of equal adjacent symbols); relative error is undefined
   there and that pair was excluded from usability ratios only.

## Conjectures and computational status

### C1 (histogram invariant) — DEAD (as predicted formally)

*Statement:* H(x,y) is usable as an edit-distance certificate
(ρ ≥ 0.90 and worst-case monotone-fit relative error ≤ 3× on the full
corpus).

*Result:* **fails both.** ρ(H, ED) = 0.635 over the n = 1000 corpus;
worst-case relative error 57× (median 1.71×). The formal counterexample
was confirmed in-corpus: adv pair seed 5002 (x = 0^n, y = (01)^{n/2}) has
H = 0 but ED = 1000 = n ≥ n/4 (pre-registered pass-through criterion).
The entire perm family (30 pairs) has H = 0 with ED ranging 0–303.
Histograms carry no certificate information beyond a weak correlation;
this is folklore, now machine-checked.

### C2 (q-gram lower bound) — KNOWN LEMMA, too weak to be a live invariant

*Statement:* LB_5 is usable (same thresholds).

*Result:* **fails both.** ρ(LB_5, ED) = 0.665 (< 0.90); worst-case
relative error 67× (median 1.02×). Median ED/LB_5 ratio by family:
planted **1.82**, rand4 **5.01**, adv **5.0**, perm-trans **8.0**,
rand2 **14.6**, perm-shuffle **15.0** (max 21.6). The bound is tightest
exactly where filtering algorithms already work (small planted distances)
and collapses on far/random and structured-permutation pairs — consistent
with why q-gram filters are used for candidate generation, not
certification. This is Ukkonen-style prior art restated; no new structure.

### C3 (sublinear-read information invariant) — probe inconclusive; failure mode is informative

*Statement (barrier form):* sketches from o(n) reads cannot predict ED
well; operationally, "information suffices" if near/far classification
error ≤ 10% at read budget r = 0.05n, "barrier-live" if error > 20% even
at r = 0.25n (random+planted fit, full-corpus evaluation).

*Result:* **neither threshold met.** Error plateaus at **14.9%** for both
r = 50 and r = 250 (18.9% at r = 10); Spearman(prediction, ED) rises only
0.58 → 0.65 across a 25× budget increase.

Where the errors sit matters more than the aggregate:
- rand4, adv-control, perm-trans, perm-blockswap (at r ≥ 50): 0% error.
- **planted-near pairs: ~61% misclassified as far** at every budget.
  Cause identified: our sketch reads *fixed offsets*, so a single
  insertion/deletion shifts all subsequent comparisons out of alignment;
  with ~7 indels among the first 250 positions the matched-index feature
  collapses toward chance (e.g., planted seed 3001, true ED = 16,
  matched-index fraction 0.36 ≈ chance for |Σ| = 4).
- adv seed 5002 (H = 0, ED = n) is classified correctly only at r = 250.

So the naive positional-agreement invariant provably dies on indels at
tiny edit rates, yet a trivially better read model (aligned windows /
seeding) would fix exactly that failure — meaning our probe bounds what
*this* sketch extracts, not what any o(n²)-time algorithm could know.
That gap is why the verdict is not clean AGAINST.

## Is a Galois-style impossibility route live?

Partially, but not through anything we formalized:

- Every cheap statistic probed is either *provably foolable* on structured
  families (histograms: rotation counterexample, ED/n = 1 at H = 0;
  fixed-offset agreement: single-indel shift collapse) or *is* a known
  bound whose looseness on the same structured families is already
  understood (q-gram LB).
- This mirrors the known reduction landscape: SETH-hardness constructions
  (e.g., Backurs–Indyk-style gadgets) succeed precisely by building
  instances that defeat local/statistical summaries. Our probing
  reconfirms computationally that such summaries are defeated, which is
  necessary but far from sufficient for a barrier theorem.
- What the experiment adds beyond folklore: a concrete, quantified
  failure taxonomy (histogram collapse at H = 0; q-gram looseness factors
  5–22 by family; indel-sensitivity of positional reads at edit rate 2%),
  i.e., a list of properties any surviving invariant must have: it must be
  alignment-robust, sensitive to rearrangement (not just composition), and
  collision-resistant at alphabet-scale birthday bounds.

## Honest caveats

1. n ≤ 2000, |Σ| ≤ 4, one predictor family (6-feature linear ridge), one
   sampling scheme. Nothing here rules out invariants outside this class;
   it only shows the obvious ones fail.
2. C3's plateau at ~15% reflects our predictor's weakness (fixed-offset
   reads, linear model), not an information-theoretic lower bound; the
   pre-registered thresholds were met from neither side, so C3's status is
   genuinely undetermined by this experiment.
3. Two pre-registration deviations occurred (both formula corrections made
   *before* looking at any analysis output, documented above). The C2
   correction in particular means C2's "known lemma" status was imposed by
   repair rather than measured from scratch.
4. Mutual information proper was not estimated; rank correlation and
   classification error on 74 classified pairs are coarse proxies.

## Next step

Formalize the *alignment-robust read model* suggested by the failure
taxonomy: allow the algorithm adaptive/equality-comparison reads
("does substring x[i:i+w] equal y[j:j+w]?") and attempt to prove a fooling
theorem — for every such sketch with polylog/√n reads there exist two
pairs (one near, one far) in the permutation-with-small-edits family that
the sketch cannot distinguish. That theorem shape is the actual
Galois-style object; if it also fails, the route should be downgraded.

## Verdict mapping (per PREREGISTER rule)

- Not INCONCLUSIVE-leaning-SUPPORT: no invariant was USABLE on the full
  corpus (C1 ρ = 0.63, C2 ρ = 0.67 < 0.90; worst-case errors 57×/67× > 3×;
  C3 error 14.9% ∉ {≤10%, >20%}).
- Not cleanly AGAINST: C1 and C2 do collapse to known/folklore statements,
  but C3 did not collapse — it left a well-characterized open gap
  (alignment-robustness) rather than reducing to a known result.
- Therefore: **INCONCLUSIVE, leaning AGAINST.** Recommend keeping the
  claim card open only for the alignment-robust fooling-theorem attempt
  above; if that fails within the cheap_falsification window, downgrade.
