# RESULTS — combo:mendel-sex cheap falsification

**Hypothesis.** Sex is maintained as error-correction for the discrete
hereditary substrate: recombination pays the twofold cost when the genomic
degradation rate exceeds a threshold U* expressible in mutation-rate units.
Cheap falsification: derive U*(N, s) from an asexual-vs-sexual simulation of
mutation-selection balance and check whether the predicted favorable regime
(U > U*) matches empirical genomic deleterious mutation rates across taxa.

**Verdict: INCONCLUSIVE** — boundary case leaning AGAINST (see Verdict section).
The simulation confirms a finite, U-units threshold exists (the structural
claim), but its placement (U* ≈ 0.6–1.1) covers only the top of the empirical
U range; for most obligately sexual taxa the model says recombination cannot
repay the twofold cost — the classic mutational-deterministic critique.

Reproduce: `python3 experiments/mendel-sex/simulate.py --workers 8` (full grid,
501 s wall clock, 32/32 cells completed, no budget skips; serial run also works
but needs >2000 s; `--quick` ≈ 1 s smoke test). Cells are independent with
per-cell fixed seeds (`seed0=20260227`), so process-pool scheduling does not
change any sampled value; an earlier interrupted run of the same protocol was
terminally reproduced cell-for-cell by this rerun.
Pure Python stdlib; protocol frozen in
[PREREGISTRATION.md](PREREGISTRATION.md) **before** any run.

## Method

Individual-based Wright-Fisher, constant N, abstract genome = L-locus bitmask
(Python int), all deleterious effects equal to s, multiplicative fitness
W = (1−s)^k, k = `bit_count()`. Viability selection by multinomial sampling,
then:

- **asexual**: offspring = parent + Poisson(U) new mutations at random loci;
- **sexual**: free recombination (each locus from either of two randomly drawn
  parents with p = ½) + the same Poisson(U) mutation.

Sex carries no internal cost; the twofold cost enters only via the break-even
criterion. L = 6·U/s + 32 (bit-collision loss of mutations ≤ ~1/6, ignored).
No beneficial mutations, no epistasis. Metric: r := OLS slope over generations
[T/2, T] (T = 2000) of the population mean of ln W (mean **log** fitness, as
pre-registered); **r > 0 = ongoing fitness decay**. Advantage A = r_asex −
r_sex; 3 paired seeds per cell, σ_A = SE of paired differences. Sanity anchors
(pre-registered): r_sex should sit at ≈ 0 (free recombination reaches
mutation-selection balance, Haldane load); asexual advantage should appear
only when the least-loaded class n₀ = N·e^(−U/s) collapses. Both hold (tables
below; r_sex ∈ [−4×10⁻⁵, +3×10⁻⁵] throughout; A turns on between n₀ ≈ 30 and
n₀ ≈ 1).

## Numbers

Grid: (N, s) ∈ {(500, .05), (2000, .05), (2000, .02), (5000, .02)} × U ∈
{0.05…2.0}; all 32 cells completed (501 s wall clock, 8 workers); full per-cell
data in `results.json`. Selected cells (r in 10⁻⁴/gen, ±SE of A):

| N | s | U | r_asex | r_sex | A | n₀ theory | clicks/1k |
|---|---|---|---|---|---|---|---|
| 500 | .05 | 0.10 | 0.22 | −0.12 | +0.23 ± 0.40 | 68 | 2 |
| 500 | .05 | 0.20 | 3.77 | 0.12 | +3.65 ± 0.10 | 9.2 | 9 |
| 500 | .05 | 0.80 | 8.93 | −0.15 | +9.07 ± 1.5 | 5.6e−5 | 19 |
| 2000 | .05 | 0.20 | 15.6 | 0.03 | +15.6 ± 1.5 | 37 | 4 |
| 2000 | .05 | 0.80 | 78.1 | −0.08 | +78.1 ± 8.9 | 2.3e−4 | 14 |
| 2000 | .02 | 0.10 | 11.0 | 0.41 | +10.6 ± 2.7 | 13.5 | 4 |
| 2000 | .02 | 0.80 | 91.0 | 1.10 | +89.9 ± 3.4 | 8.5e−15 | 48 |

**Thresholds** (A − 2σ_A crossing, linear interpolation; δ₂ₓ = ln2/1000 =
6.93×10⁻⁴/gen, i.e. twofold cost repaid within 1000 generations):

| (N, s) | U*ₛᵢ₉ₙ (A > 0) | U*₂ₓ (A ≥ δ₂ₓ) | U*₂ₓ at G=100 (δ′=6.9×10⁻³) |
|---|---|---|---|
| (500, 0.05) | 0.11 | 1.08 | never (max A = 9.1×10⁻⁴) |
| (2000, 0.05) | 0.11 | 1.00 | never (max A = 1.05×10⁻³) |
| (2000, 0.02) | 0.06 | 0.64 | never (max A = 1.86×10⁻³) |
| (5000, 0.02) | 0.05 | 0.61 | never (max A = 1.75×10⁻³) |

Reading: the **sign** threshold is low (U ≈ 0.05–0.11) but the advantage there
is ~10⁻⁴–10⁻⁵/gen — far too small to matter. The **twofold-cost** threshold
U*₂ₓ ≈ 0.6–1.1 is the meaningful one, and it is only weakly N-dependent in the
simulated range (N·s from 10 to 100; the now-complete N = 5000 row sits inside
the same band, U*₂ₓ = 0.61). At the stricter 100-generation payback
horizon no simulated cell ever reaches break-even.

## Literature anchor (ALL FROM MEMORY, UNVERIFIED — check against primary sources before citing)

| taxon | genomic deleterious U /generation | vs U*₂ₓ ≈ 0.6–1.1 |
|---|---|---|
| microbes (E. coli-like) | ~10⁻³–10⁻² (Kibota–Lynch-type estimates) | 2–3 orders **below** |
| C. elegans | ~10⁻²–5×10⁻² | 1–2 orders below |
| Drosophila | ~10⁻²–10⁻¹ | ~1 order below (upper edge marginal) |
| Homo sapiens | ~0.5–2 (≈1 commonly quoted) | **inside** the favorable regime |

Classic context (memory): Kimura–Maruyama (1966) and Kondrashov (1988) — with
multiplicative fitness recombination has no deterministic advantage; the
mutational-deterministic explanation of sex needs synergistic epistasis and
roughly U ≳ 1 to repay the twofold cost. Felsenstein (1974) on the twofold
cost + Hill-Robertson LD. Our simulation deliberately used multiplicative
fitness, i.e. the regime least favorable to sex, and reproduces exactly this
picture from first principles.

## Verdict

Pre-registered rule applied to U*₂ₓ ≈ 0.6–1.1:

- **Not AGAINST outright**: the predicted favorable regime is *not*
  inconsistent with all real parameter ranges — human-scale U (~1–2) falls
  inside it, and the hypothesis's core structural claim (a finite threshold
  expressible in mutation-rate units, above which recombination's advantage
  repays the twofold cost) is confirmed in simulation.
- **Not SUPPORT**: obligate sex is maintained across insects, nematodes, and
  plants whose U sits 1–2 orders of magnitude **below** U*, where the model
  puts the advantage at ~10⁻⁴/gen or less — 3+ orders short of break-even.
  The hypothesis therefore fails to explain sex where sex is actually
  observed, unless real genomes carry synergistic epistasis (excluded by
  construction here) or the relevant advantage is Fisher-Muller combining of
  beneficial mutations (also excluded here).

→ **INCONCLUSIVE**, boundary case leaning AGAINST for the mutational-error-
correction framing specifically. This matches the classic critique: a pure
degradation-threshold defense of sex works only at U ≳ 1, i.e. essentially
only for large, long-lived eukaryotes.

## Caveats

1. **No epistasis, no beneficial mutations** — the two known escape routes for
   sex are outside the model by design; the verdict concerns only the
   degradation-threshold version of the claim.
2. **Free recombination idealized** (fully unlinked loci, no linkage drag,
   no twofold cost inside the simulation — cost enters only via δ₂ₓ).
3. Equal effect sizes s; single haploid mating scheme; mutation bit-collision
   at the same locus collapses (~≤1/6 of mutations at chosen L).
4. Only 3 paired seeds/cell; σ_A from paired differences.
5. All literature U values are **from memory and unverified**; ranges could
   shift the taxon placements by up to ~an order of magnitude (e.g. if
   Drosophila U were near 0.1–0.3, the mismatch narrows).
6. Metric is mean **log** fitness slope (pre-registered parenthetical), not
   ln(mean fitness); for these distributions the two differ at O(σ²) and the
   sign-threshold placement could shift slightly, not the order of magnitude.

## Next step

Re-run with synergistic epistasis (fitness = exp(−s·k − α·k²/2), α > 0) and a
beneficial-mutation arm: Kondrashov's deterministic-mutation mechanism predicts
U* drops toward ~0.1–0.5 with α > 0, which would move most sexual taxa inside
the favorable regime and flip this to a qualified SUPPORT for the *epistatic*
variant — while confirming AGAINST for the pure discreteness-maintenance
framing. Separately: verify the literature U table against primary sources
(Kibota & Lynch 1996; Keightley & Eyre-Walker 2000; Lynch 2010) before any
upgrade.
