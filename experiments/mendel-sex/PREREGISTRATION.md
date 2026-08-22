# PREREGISTRATION — combo:mendel-sex cheap falsification

Written **before** any simulation result was computed. The simulation code
(`simulate.py`) implements exactly this protocol; criteria below were fixed
before running it beyond a timing smoke test.

## Claim under test

`combo:mendel-sex`: sex is maintained as error-correction for the discrete
hereditary substrate; recombination pays the twofold cost when the genomic
degradation rate exceeds a threshold expressible in mutation-rate units U*.

Cheap falsification (from the claim card, operationalized for `simulable`
verification): translate the hypothesis into a threshold prediction U*(N, s),
then ask whether the predicted favorable regime (U > U*) matches the range of
empirical genomic deleterious mutation rates across taxa.

## Model (fixed in advance)

Individual-based Wright-Fisher, pure Python stdlib, fixed seeds.

- Genome abstracted to an L-locus bitmask (Python int); every deleterious
  mutation has the same heterozygous-equivalent effect s; fitness is
  multiplicative: W = (1−s)^k, k = mutation count (`int.bit_count()`).
- Constant population size N. Each generation: viability selection by
  multinomial sampling weighted by W, then reproduction.
- **Asexual**: offspring = parent genome + new mutations, n ~ Poisson(U),
  each at a uniformly random locus (bit set; collisions collapse — mitigated
  by choosing L ≥ 6·U/s + 32 so saturation is negligible).
- **Sexual** (free recombination, unlinked loci): offspring draws two parents
  independently from the same post-selection pool; each locus inherited from
  parent 1 or 2 with probability ½ (random L-bit mask), then Poisson(U) new
  mutations. Sex pays **no** built-in cost inside the simulation; the twofold
  cost enters only through the break-even criterion below.
- Initialization: all genomes mutation-free. No beneficial mutations, no
  epistasis, no recombination linkage structure beyond free recombination.
- Recorded per generation: ln W̄ (mean log fitness), mean k, min k.

## Metrics

- Degradation rate r := OLS slope of ln W̄ over the measurement window
  [T/2, T]. r < 0 means ongoing fitness decay (Muller's ratchet / drift load).
- Advantage A(U) := r_asex(U) − r_sex(U). A > 0 = recombination slows
  genomic degradation. Replicates: R ≥ 3 seeds per cell; σ_A = standard error
  of the per-replicate differences.

## Threshold definitions (fixed now)

- **U\*ₛᵢ₉ₙ(N,s)**: smallest grid U where A(U) − 2σ_A(U) > 0 (advantage
  survives 2 SE of replicate noise), linear interpolation between grid points.
- **U\*₂ₓ(N,s)**: smallest grid U where A(U) ≥ δ with δ = ln 2 / 1000 ≈
  6.93×10⁻⁴ per generation — i.e. the degradation-rate gap must repay the
  twofold cost of sex within a 1000-generation horizon. Sensitivity check at
  δ′ = ln 2 / 100.

Expected sanity anchor (also pre-registered): with purely multiplicative
fitness there is **no deterministic** (N→∞) advantage of recombination, so any
A > 0 must come from finite-N drift/Hill-Robertson effects and should vanish
as N·s grows or U/s shrinks (least-loaded class n₀ = N·e^(−U/s) ≫ 1). If A > 0
persists at n₀ ≫ 1, suspect a bug.

## Verdict rule (fixed now)

Empirical genomic deleterious mutation rates per generation (from memory,
UNVERIFIED — must be labeled as such in RESULTS):

| taxon | U (per generation) |
|---|---|
| microbes (E. coli-like) | ~10⁻³ – 10⁻² |
| C. elegans | ~10⁻² – 5×10⁻² |
| Drosophila | ~10⁻² – 10⁻¹ |
| Homo sapiens | ~0.5 – 2 |

- **SUPPORT (upgrade path)**: the predicted favorable regime (U > U*) sits
  within one order of magnitude of the U-range of taxa that actually maintain
  regular sex (animals, U ~ 0.1–2), AND excludes the microbe range
  (U ≪ U*) — i.e., the threshold lands where biology switches reproductive mode.
- **AGAINST**: U* exceeds the U of known obligately sexual taxa by more than
  an order of magnitude at all simulated (N, s) (classic mutational-
  deterministic critique: recombination cannot repay the twofold cost at real
  mutation rates without synergistic epistasis).
- **INCONCLUSIVE**: partial overlap or margin within ~1 order of magnitude of
  the boundary case.

## Compute budget

Hard cap 2400 s wall clock for the full grid (task budget ~40 min). The
driver enforces the cap, reports elapsed time and any cells skipped by the
cap. Pure Python stdlib; fixed RNG seeds for reproducibility.
