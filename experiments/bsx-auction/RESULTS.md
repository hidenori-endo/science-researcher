# EXPERIMENT: bsx-auction — prior-free posted pricing as a portfolio over prices

Claim: `combo:black-scholes-auctions` (hypothesis, speculative).
Cheap falsification (from card metadata): "Single-item case: does a dynamic
portfolio of posted prices replicate the optimal-distribution benchmark within
constant factor without samples? If even this fails, combinatorial version
hopeless."

---

## PRE-REGISTRATION (written before any result was computed)

### Model

- Single item, T = 2000 rounds, one buyer per round with value v_t ∈ (0, 1].
- Each round the policy posts a price p_t from a **fixed public grid**
  G = {1/16, 2/16, ..., 16/16} (n = 16 prices). Sale iff v_t ≥ p_t; revenue p_t.
- **Bandit feedback only**: the policy observes whether the sale happened (and
  its own revenue). It never observes v_t on rejection. No samples of the value
  distribution are given to any policy; the grid and T are the only prior
  information (values are normalized into a known bounded range [0,1], the
  standard prior-free pricing assumption).

### Policies (all sample-free; declared before evaluation)

1. `uniform-mix` — uniform random choice over the grid each round (pure
   portfolio baseline; guarantees CR ≤ n = 16 in expectation by an averaging
   argument, independent of the instance).
2. `exp3` — exponential weights over prices with importance-weighted rewards,
   γ = min(1, √(n·ln n / T)).
3. `exp3-anytime` — same with the decreasing schedule γ_t = min(1, √(n·ln n / t))
   (unknown-horizon variant).
4. `eps-greedy` — ε = 1/n forced uniform exploration, otherwise the empirically
   best price (stochastic-friendly, adversarially weaker; included as a
   candidate, expected to fail on adversarial orders).
5. `ucb1` — standard UCB1 treating each price as an arm with revenue rewards.

### Value families (declared before evaluation)

IID families (30 seeds each, fresh stream per seed):

- `uniform01` — v ~ U(0,1).
- `powlaw` — power law on [0.01, 1], density ∝ v^{-1.5} (inverse-CDF sampling).
- `bimodal` — 0.5·U(0, 0.15) + 0.5·U(0.6, 1.0).
- `lognormal` — LogNormal(μ=-2, σ=0.75) clipped to (0,1] (clipping noted as caveat).

Adversarial permutation families (multiset fixed, order adversarial; the
policy sees the stream in that order). Instances per multiset: ascending sort,
descending sort, and 10 seeded random shuffles. Worst instance governs:

- `perm-spike-zero` — multiset {1.0} × 1 ∪ {0.0} × (T−1): one big buyer, rest
  buy nothing. Best fixed price earns exactly 1.0 (sell once at p ≤ 1).
- `perm-two-level` — {1.0} × T/2 ∪ {0.4} × T/2.
- `perm-wide-tail` — {1.0}×3 ∪ {0.7}×27 ∪ {0.02}×(T−30).

### Benchmarks

- **Clairvoyant optimal fixed price** (primary): with full knowledge of the
  distribution (IID) or multiset (permutations), max over p ∈ (0,1] of
  p·P(v ≥ p). Exact for permutations; Monte Carlo with 200 000 draws for IID
  families (approximation error ≪ thresholds).
- **Myerson optimal** (secondary, reported only): for a single IID buyer the
  Myerson mechanism *is* a posted price, so Myerson optimal revenue coincides
  with the clairvoyant best fixed price; we report it as the same number. The
  grid-constrained optimum is also reported to separate "portfolio over grid"
  loss from "grid discretization" loss.

### Metric

CR(family, policy) = clairvoyant-fixed revenue ÷ policy revenue, ≥ 1.
- `CR_mean` — over the family's seeds/instances of mean revenue.
- `CR_worstseed` — max over seeds/instances of per-seed CR (capped at 1000;
  a 0-revenue seed is reported as > cap).

### Pass/fail criteria (fixed before computation)

- **SUPPORT** (upgrade path): ∃ policy π such that for **every** listed family:
  CR_mean(family, π) < 10 **and** CR_worstseed(family, π) < 50, with zero
  samples used. (The worst-seed guard prevents SUPPORT from resting on seed
  luck.)
- **AGAINST**: **every** policy π has CR_mean > 50 on at least one natural
  family.
- **INCONCLUSIVE**: neither (including mixed outcomes, e.g. some policies pass
  the 10 bar and others blow up).

### Scope caveats declared up front

- The adversarial families are **oblivious orders of a fixed multiset**
  (permutation model). A fully adaptive adversary that observes the policy and
  adapts values can defeat any algorithm in this model (known limitation of
  dynamic pricing against adaptive adversaries); that stronger threat model is
  out of scope for this falsification test.
- Values are assumed normalized to a known range [0,1]. Unknown scale is a
  different (harder) problem.
- n = 16 grid: uniform-mix alone certifies CR ≤ 16 always; the question is
  whether hedging policies get the constant well below 10 in practice.

---

## RESULTS (filled in after running `python3 run_experiment.py`)

Full run: T = 2000, 30 IID seeds/family, 12 permutation instances/multiset
(asc, desc, 10 shuffles) × 3 repetitions each, grid n = 16. Wall clock
**19.8 s** (cap 40 min). Cells: CR_mean (for perm families: worst instance of
mean CR) / CR_worstseed.

| family | uniform-mix | exp3 | exp3-anytime | eps-greedy | ucb1 | opt-fixed | opt-grid |
|---|---|---|---|---|---|---|---|
| uniform01 | 1.50 / 1.6 | 1.26 / 1.3 | 1.19 / 1.3 | 1.08 / 1.2 | 1.30 / 1.4 | 498.38 | 497.90 |
| powlaw | 1.56 / 1.8 | 1.48 / 1.8 | 1.42 / 1.6 | 1.19 / 1.5 | 1.51 / 1.8 | 56.50 | 56.33 |
| bimodal | 1.81 / 1.9 | 1.42 / 1.6 | 1.30 / 1.4 | 1.16 / 1.4 | 1.48 / 1.6 | 597.72 | 584.08 |
| lognormal | 2.58 / 3.1 | 2.23 / 2.6 | 1.93 / 2.2 | 1.16 / 1.4 | 2.30 / 2.8 | 135.96 | 135.69 |
| perm-spike-zero | 2.82 / 16.0 | 5.33 / 16.0 | 4.36 / 16.0 | 16.00 / 16.0 | 16.00 / 16.0 | 1.00 | 1.00 |
| perm-two-level | 1.66 / 1.7 | 1.35 / 1.4 | 1.55 / 1.6 | 1.26 / 1.4 | 1.45 / 1.4 | 1000.00 | 1000.00 |
| perm-wide-tail | 5.60 / 6.5 | 5.32 / 7.1 | 5.52 / 7.0 | 17.78 / 22.9 | 7.11 / 7.1 | 40.00 | 20.63 |

(`opt-fixed` is the clairvoyant TOTAL revenue over the horizon; for a single
IID buyer Myerson optimal = clairvoyant best fixed price, as pre-registered.)

### Criteria check (mechanically applied to results.json)

| policy | mean-CR < 10 on all families | worst-seed CR < 50 on all families |
|---|---|---|
| uniform-mix | yes | yes |
| **exp3** | **yes** | **yes** |
| exp3-anytime | yes | yes |
| eps-greedy | no (16.00 on perm-spike-zero, 17.78 on perm-wide-tail) | yes |
| ucb1 | no (16.00 on perm-spike-zero) | yes |

Both failing policies miss the bar through the same structural event on
`perm-spike-zero` described in caveat 2 below; eps-greedy additionally
degrades on `perm-wide-tail` for genuinely mechanism-level reasons.

### Key observations

1. **Hedging portfolios pass everywhere; estimation-greedy policies do not.**
   EXP3-style exponential-weights mixing achieves CR_mean ≤ 5.33 and
   CR_worstseed ≤ 16 across *all seven* families with zero samples. In
   contrast, eps-greedy — which estimates per-price means and exploits —
   degrades to 17.78× on `perm-wide-tail`. This is exactly the hypothesized
   mechanism signature: robustness comes from maintaining a portfolio over
   instruments, not from learning the distribution.
2. The worst-seed floor of 16.0 on `perm-spike-zero` is structural: the single
   high-value buyer may arrive in round 1 while the portfolio happens to post
   its cheapest grid price (UCB1 plays arm 1 first deterministically → CR =
   16 exactly). Any fixed n-price portfolio has this n-factor arrival-timing
   floor; it is discretization, not distributional failure.
3. On smooth families the hedging policies sit within 1.2–2.6× of the
   clairvoyant optimum — close to the √(nT) regret prediction relative to
   horizon revenue.

## Verdict

**UPGRADE-path SUPPORT**, per the pre-registered criteria: the sample-free
portfolio policies `exp3`, `exp3-anytime`, and even the pure `uniform-mix`
achieve CR_mean < 10 AND CR_worstseed < 50 against the clairvoyant
fixed-price benchmark on every test family with zero samples. No policy blew
up > 50× anywhere, so AGAINST does not apply.

Per AGENTS.md: SUPPORT here means only that the cheap falsification stage is
passed and the claim advances to the next falsification stage with stricter
criteria — the hypothesis is not "solved".

## Honest caveats

- **Oblivious adversaries only.** Adversarial families are fixed multisets in
  adversarial orders (permutation model). A fully adaptive adversary that
  reacts to the policy's past prices can drive any algorithm's ratio up;
  that threat model was declared out of scope before the run.
- **Known value scale.** Values are normalized to [0,1] and the grid is built
  on that knowledge. Unknown-scale markets are untouched by this experiment
  (lognormal was clipped to [0,1]; clipping slightly flatters the policies).
- **Grid-constrained vs continuous benchmarks diverge when mass sits below the
  cheapest price**: on `perm-wide-tail` the continuous optimum (price 0.02,
  revenue 39.4) is far above the grid optimum (20.6), yet policies still stay
  within ~7× of the *continuous* optimum — reported transparently rather than
  hidden behind the easier grid benchmark.
- Monte Carlo clairvoyant (200k pooled draws) approximates the IID optimum;
  error ≪ thresholds.
- Single-buyer-per-round, single-item setting; revenue = posted price on sale.
  The card's combinatorial/multi-bidder version remains untested.

## Next step (stricter re-registration for the next stage)

1. Remove the known-scale assumption: portfolio over *geometric* grids with
   doubling-style scale search; require constant CR on scale-misspecified
   families.
2. Prove formally what the experiment suggests: EXP3-over-prices guarantees
   CR ≤ min(n, 1 + O(√(n ln n / T))) against oblivious sequences — turning the
   empirical constant into a theorem would upgrade this from simulable to a
   formal result.
3. Only then attempt the combinatorial analogue named in the card
   (`failure.axis`: whether allocation discreteness blocks replication).
