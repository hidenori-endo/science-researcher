# RESULTS — experiments/prion-glass

Target claim: `combo:prion-glass` — "glassy arrest as self-templated
configurational order". Registered cheap falsification: check whether locally
ordered regions grow by boundary-conversion kinetics (templated) versus bulk
nucleation, via distinguishable growth-law exponents, against an annealed
(non-glassy) control at the same parameters.

**Verdict: INCONCLUSIVE** (pre-registered criteria, amendment v2/v2.1).

## Method

2D Ising model, H = -J Σ⟨ij⟩ s_i s_j (J=1), L=126 square lattice, periodic,
instant quench from p=0.5 random to T=1.5 (< Tc = 2.269), heat-bath updates.
Spin-flip KCM: a spin updates only if it has ≥ f unlike neighbours *before*
the update. A flip is its own reverse and the facilitated kernel is the exact
conditional of π ⇒ detailed balance holds exactly for any f.

- GLASS channel: f=2 (FA-type facilitation; ordered interiors immobile).
- CONTROL channel ("annealed crystallisation"): f=0, identical Hamiltonian /
  T / L / quench.
- Ablation: f=3, 1 seed.

Local-order observable: non-overlapping 3×3 blocks, ordered if |block mag| ≥ 7/9;
4-connected same-sign clusters on the 42×42 block grid; r_mean =
√(total ordered area / #clusters). Templating statistic φ_temp = fraction of
newly ordered blocks 4-adjacent to previously ordered blocks, with a random
placement null (20 draws); Avrami exponent n from f_exc ∈ [0.15, 0.70];
growth exponent α from r_mean over [1.5·r(t_early), 0.93·r_plat], ≥6 points
spanning ≥0.4 decades.

Production: 3 seeds × {GLASS, CONTROL} + 1 ablation, 12000 sweeps each.
Compute: **1085 s total (~18 min)**, every run finished its sweep budget well
under the 400 s/run guard. Pure Python stdlib (`sim.py`, `analyze.py`).

## Pre-registration status (honest history)

`PRE_REGISTRATION.md` v1 was written by an earlier session before any data.
It mismatched its own implementation (constraint m, observable definition);
its pilot parameters produced no measurable growth window (m=2 stalled,
m=3 froze). This session amended it to v2 (spin-flip model, thresholds S1–S4 /
A1–A2 carried over verbatim where applicable) and v2.1 (T: 1.0 → 1.5;
t_early re-anchored), **in both cases before a single fit or verdict number
existed**. Two production batches were rejected as inadmissible under the
registered windows and are archived untouched:

- T=1.0 batch (`data_t10_rejected/`): ordering avalanche completes before the
  first checkpoint (f_ord ≈ 0.84 at t=50); α window empty.
- Pilot lattice-gas batch (`data_pilot/`, prior session): no growth in GLASS.

No threshold was changed after seeing any fit output. The verdict rules below
are exactly those locked in the amendments.

## Numbers

Per-replica fits (registered windows):

| replica | α (R²) | n_Avrami | φ_temp / φ_null | persistence(end) | growth ratio |
|---|---|---|---|---|---|
| glass_f2_s1 | — (empty window) | — | — | 0.112 | 1.87 |
| glass_f2_s2 | 0.175 (R²=0.79) | — | — | 0.102 | 3.29 |
| glass_f2_s3 | 0.077 (R²=0.49) | — | — | 0.093 | 3.44 |
| control_s1 | 0.085 (R²=0.43) | — | — | 0.000 | 4.41 |
| control_s2 | 0.169 (R²=0.59) | — | — | 0.000 | 4.43 |
| control_s3 | 0.195 (R²=0.84) | — | — | 0.000 | 4.56 |
| ablation f=3 s1 | freeze at f_ord=0.392, mobility→0 by construction of window: no growth law measurable | | | | 1.00 |

Mechanistic observations (descriptive, not registered diagnostics):

- **Avalanche**: both channels reach f_ord ≈ 0.81–0.84 within the first
  checkpoint interval (t ≤ ~100 sweeps): the transformation is dominated by
  parallel local alignment, not by propagating interfaces or droplet
  nucleation. The registered Avrami window [0.15, 0.70] is crossed entirely
  between checkpoints t=0 and t≈77 ⇒ n and φ uncomputable for every replica.
- **Post-avalanche coarsening**: r_mean grows only ~3–4.5× before finite-size
  saturation; effective α ≈ 0.08–0.20 in BOTH channels (merge-jump-dominated
  staircase; R² 0.43–0.84), far below Allen-Cahn 1/2.
- **Freezing**: GLASS mobility → 0 at t ≈ 2700–4800 (all 3 seeds) while
  CONTROL never freezes; mean new-ordered-blocks per checkpoint after t=5000:
  GLASS 0.0 vs CONTROL 10.6–12.8 (thermal de-novo islands keep appearing only
  in the annealed channel). persistence(end): GLASS 0.093–0.112 vs CONTROL
  0.000.

## Verdict logic (registered)

Gates: measurability PASS (glass grows, α window exists in 2/3 replicas);
arrest FAIL marginally (persistence 0.097 < 0.10 threshold).

- S1 (φ_temp ≥ 0.75): FAIL (uncomputable — empty Avrami window).
- S2 (null ratio ≥ 2): FAIL (uncomputable).
- S3a (α_G + 0.06 < α_C): FAIL; S3b (α_C ∈ [0.40, 0.60]): FAIL (α_C = 0.15).
- S4 (n < 1.0): FAIL (uncomputable).
- A2a / A2b: not met either (α difference within noise but control insane;
  n uncomputable).

⇒ **INCONCLUSIVE**, on two independent registered grounds: the control sanity
guardrail (α_C outside band ⇒ pipeline/regime suspect regardless of GLASS
numbers) and the uncomputability of S1/S2/S4.

## Honest interpretation

- The experiment does NOT support the prion-templating hypothesis at this
  stage; neither does it refute it. What it shows is that **the registered
  growth-law diagnostics lack discriminating power in this surrogate regime**:
  a deep quench converts most of the disorder by constraint-permitted parallel
  local alignment (facilitation is abundant early), so neither bulk nucleation
  nor templated boundary conversion is the rate-limiting process whose exponent
  could be measured. The card's failure mode ("templating adds nothing
  falsifiable") is thus partially realised in a weaker form: as instrumented,
  templating left no measurable kinetic signature distinct from the annealed
  channel — but for reasons of observables/window placement, not because the
  channels behaved identically (they differ qualitatively in freezing,
  persistence and late-time island creation).
- The surrogate is a spin KCM, not a structural glass: "arrest" is imposed by
  construction (interiors immobile at f≥2), vibrational/caging physics absent.
  Any SUPPORT here would only have meant advancing one rung on the
  falsification ladder, per repo policy.
- Amendment history involves two rejected production batches; all raw data are
  committed for audit. Seeds are shared between channels (paired comparison),
  n=3 per arm — spread reported as min/max, no significance testing attempted.

## Next step (sharper falsification stage)

1. **Seeded-front experiment**: prepare post-avalanche configurations, embed a
   single ordered domain in a disordered matrix, measure front position R(t)
   directly per channel. Removes merge-event contamination and gives clean
   interface-limited velocity/exponent without census statistics.
2. Capture the avalanche itself (checkpoints log-spaced from t≈5) and test
   whether it is nucleation-like (cluster births spatially Poisson),
   alignment-like, or contact-templated (births ring existing domains) — the
   φ_temp/null machinery is designed for exactly this regime and was simply
   not sampled finely enough here.
3. If (2) shows contact-templated avalanche kinetics distinct from the
   annealed control's Poisson births, re-register with stricter thresholds and
   larger n before any upgrade of the claim stage.
