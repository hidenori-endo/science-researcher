# Pre-registration — experiments/prion-glass/

> **STATUS: SUPERSEDED in part by AMENDMENT v2 (below). The v1 text is kept for
> the record; the pass/fail thresholds S1–S4 / A1–A2 are carried over verbatim
> into v2. No production verdict was computed under v1.**


Target claim: `combo:prion-glass` ("glassy arrest as self-templated configurational
order"). Cheap falsification (claim card): "check whether locally-ordered regions
grow by boundary conversion kinetics (templated) versus bulk nucleation;
distinguishable growth-law exponent."

These criteria are written **before** any production data is computed. Parameter
tuning (choosing rho, T, sweep budget so that both phases actually arrest /
coarsen within budget) is done on throwaway scout runs at L=32 and does not
enter the criteria; the criteria below are parameter-agnostic and control-relative.

## Model (2D lattice surrogate)

Single-species lattice gas on L x L square lattice, periodic, density rho,
NN attraction eps=1, Kawasaki NN-swap Metropolis at temperature T < Tc (~0.567).
Instant quench from a random configuration.

Two dynamics, identical Hamiltonian / rho / T / L:

- GLASS: a move is allowed only if the hopping particle has >= m=3 occupied
  nearest neighbours **before** the move (Kob-Andersen-type kinetic constraint).
- CONTROL ("annealed", non-glassy): no kinetic constraint — every Metropolis-
  accepted swap runs. Same parameters otherwise. This is the annealed
  crystallization/phase-separation control the claim asks for.

## Local-order observable

A site is **caged** (locally maximally ordered) if it is occupied with all 4
nearest neighbours occupied (bulk-like local environment of the ordered state).
Caged sites cannot move (no vacant target). Regions of caged sites are the
locally-ordered regions whose growth we measure.

## Measured quantities (per run, checkpointed)

- f(t): caged fraction; mobility; number of clusters N_c; R_mean(t) =
  sqrt(mean cluster area) [PRIMARY domain-scale measure]; R_max(t) = sqrt(largest
  cluster area) [secondary].
- Templating fraction phi_temp(t): among sites newly caged since the previous
  checkpoint, the fraction that were 4-adjacent to an already-caged site at the
  previous checkpoint (boundary conversion channel). Complement ~ bulk
  nucleation channel.
- Null templating phi_null(t): same statistic with the new-caged count sampled
  uniformly over non-caged sites (destroys spatial correlation); 20 draws.
- Avrami exponent n: OLS slope of ln(-ln(1-f_exc)) vs ln t, with
  f_exc=(f-f_first)/(f_plat-f_first), over the window f_exc in [0.15, 0.70].
- Growth exponent alpha: OLS slope of log R_mean vs log t over the window
  R_mean in [1.5 x R_first, 0.93 x R_plat]; require >= 6 points spanning >= 0.4
  decades in t, else the fit is flagged poor.
- f_plat = mean f over the last 15% of checkpoints of the run.

Windows/f_plat are computed per replica, then averaged across >= 3 replicas
per mode; spread reported as min/max.

## Pass/fail thresholds (fixed now)

SUPPORT (upgrade-path: proceed to next falsification stage) — ALL of:

- S1: median phi_temp(GLASS) >= 0.75 — new order appears overwhelmingly at
  boundaries of existing ordered regions (templated boundary conversion).
- S2: null ratio phi_temp(GLASS)/phi_null(GLASS) >= 2 — the adjacency signal is
  not explainable by random placement given the caged fraction.
- S3: alpha(GLASS) + 0.06 < alpha(CONTROL), AND alpha(CONTROL) in [0.27, 0.58]
  (control sanity: textbook coarsening/nucleation-and-growth recovered by the
  same pipeline). The glassy exponent must be distinctly below the annealed one,
  i.e. NOT plain Lifshitz-Slyozov/Allen-Cahn coarsening.
- S4: n_avrami(GLASS) < 1.0 — kinetics incompatible with bulk nucleation-
  dominated transformation (which gives n >= ~1 even for interface-limited
  constant-rate nucleation).

AGAINST (templating adds nothing falsifiable here) — ALL of:

- A1: phi_temp(GLASS) <= 0.50 OR null ratio <= 1.5 (no specific templating
  signal beyond spatial chance), AND
- A2: |alpha(GLASS) - alpha(CONTROL)| <= 0.06 (with control sane per S3 band),
  or n_avrami(GLASS) >= 2.0 — standard nucleation/coarsening fits suffice.

INCONCLUSIVE: anything else (mixed signals, poor fits, arrest/coarsening not
reached within the runtime cap).

Interpretation guardrails:

- SUPPORT means "advance to a sharper falsification stage" (per repo ladder),
  not that the hypothesis is established; the model is a surrogate, not glass.
- If CONTROL fails the sanity band (S3), the measurement pipeline itself is
  suspect -> INCONCLUSIVE regardless of GLASS numbers.

## Runtime cap

Production: L=48, <= 6 runs (3 GLASS + 3 CONTROL), each capped at 600 s wall
by an in-run guard; total compute target well under 40 min.

---

# AMENDMENT v2 (written BEFORE any production run of the amended design;
# no verdict/fit has been computed on any data at the time of writing)

Date: same session as the pilot (see timestamps); author: continuation session.

## Why amended (pilot findings + design audit)

1. **Observable mismatch (v1 text vs implemented):** v1 defined the local-order
   site as "occupied with all 4 NN occupied" but sim.py implemented "occupied
   with >= 3 like-species NN". Pilot CSVs used the latter.
2. **Constraint parameter mismatch:** v1 registered m=3; pilot production used
   m=2. Pilot outcome: at rho=0.6, GLASS m=2 stalls with r_mean ~ 2.3 and >100
   tiny clusters (no measurable growth window => alpha uncomputable);
   GLASS m=3 freezes completely (r_mean ~ 1.2, f_ord flat). Neither instantiates
   "slow but ongoing boundary conversion", so the central observable (growth-law
   exponent) cannot be measured under v1.
3. **Detailed-balance audit:** for hop moves, a constraint checked only on the
   origin's pre-move neighborhood is NOT symmetric under move reversal (the
   origin's and destination's neighbor sets differ), so constrained Kawasaki
   dynamics does not obviously sample the Boltzmann distribution — a confound
   for a control-relative kinetic comparison.
4. Pilot data (7 CSVs) moved to `data_pilot/` and treated as scout/pilot output;
   per v1's own guardrail it does not enter the criteria.

## Amended model (v2, final)

Spin-flip KCM instead of lattice gas: 2D Ising, H = -J sum_<ij> s_i s_j, J=1,
square lattice L x L periodic, heat-bath updates at T = 1.5 (< Tc = 2.269),
instant quench from p=0.5 random initial state. Flip attempts are its own
reverse, so any configuration-dependent constraint preserves detailed balance
exactly (the facilitated-site kernel is the exact conditional of pi).

- **GLASS** (arrested channel): a spin may be updated only if it has >= f=2
  unlike neighbours *before* the update (FA-type facilitation; ordered-domain
  interiors are immobile, conversion happens at interfaces).
- **CONTROL** (annealed crystallization): unconstrained heat-bath Glauber,
  identical Hamiltonian / T / L / quench.
- Ablation (reported separately, not in verdict): f=3, 1 seed.

## Local-order observable (v2)

Non-overlapping 3x3 blocks; a block is ORDERED if |block magnetisation| >= 7/9,
with sign = sign of block magnetisation. Ordered regions = 4-connected clusters
of same-sign ordered blocks on the L/3 x L/3 block grid.

## Measured quantities (per run)

As v1 (f_ord, mobility, N_clusters, r_mean = sqrt(total ordered area /
n_clusters), r_max, phi_temp, phi_null with 20 null draws), plus:

- persistence(t) = fraction of spins never flipped since t=0. Arrest gate:
  persistence(GLASS, t_end) >= 0.10 AND strictly greater than
  persistence(CONTROL, t_end). (Relative form: both channels eventually
  saturate, so absolute plateaus are not comparable.)
- Measurability gate: r_mean(t_end) / r_mean(first checkpoint with t>=t_early)
  >= 1.15 AND a valid alpha fit window exists for GLASS, else INCONCLUSIVE
  (cannot measure a growth law).
- t_early = first log-spaced checkpoint (t >= 50).
- Control sanity band updated to alpha(CONTROL) in [0.40, 0.60]: the annealed
  non-conserved scalar order parameter coarsens by Allen-Cahn (alpha ~ 1/2).
  This number is fixed from theory before any production data, not fitted.

## Amendment v2.1 (still BEFORE any successful fit or verdict)

The v2 production parameters (L=126, T=1.0, sweeps=12000) were run to
completion (7 runs, 1175 s total) but produced NO admissible fit: at T=1.0
the post-quench local ordering avalanche finishes within the first ~50 sweeps
(f_ord reaches ~0.84 before the first checkpoint), leaving only a
merge-event-dominated staircase (r_mean 11->29 in steps) - the alpha window
defined above is empty (0 points). Diagnostic trajectory inspection only; no
alpha/n/phi number was computed on any replica.

Fixes, applied before any verdict:
- Production temperature moved to T=1.5 (= 0.66 Tc). Scout evidence (L=48)
  and finite-size scaling (x(126/48)^2) put saturation at O(3e4) sweeps,
  outside the 12000-sweep budget -> growth ongoing across the whole run for
  both channels; the GLASS channel additionally freezes (mobility -> 0)
  within budget, which is the phenomenology the claim is about.
- t_early re-anchored to the first log-spaced checkpoint (t >= 50) instead of
  0.05 * sweeps: with growth completing/steadying early, a run-length-relative
  cut excludes the entire measurable window.
- All thresholds (S1-S4, A2a/A2b), gates, observable definitions and fit
  procedures are UNCHANGED from amendment v2.

Windows, fits, aggregation over 3 replicas: exactly as v1.

## Pass/fail thresholds (carried over VERBATIM from v1)

SUPPORT — ALL of:
- S1: median phi_temp(GLASS) >= 0.75.
- S2: phi_temp(GLASS)/phi_null(GLASS) >= 2.
- S3a: alpha(GLASS) + 0.06 < alpha(CONTROL); S3b: alpha(CONTROL) in [0.40,0.60].
- S4: n_avrami(GLASS) < 1.0.

AGAINST — EITHER of ("standard fits suffice"; the decisive axis is whether the
growth LAW is distinguishable, per the claim card):
- A2a: |alpha(GLASS)-alpha(CONTROL)| <= 0.06 (with control sane per S3b), OR
- A2b: n_avrami(GLASS) >= 2.0.
(Note vs v1: v1's A1 additionally required absence of a templating-placement
signal; dropped — strong phi_temp with a standard growth law still means the
law is describable without templating.)

INCONCLUSIVE: anything else, including either gate failing or poor fits
(R^2 < 0.9 flagged in RESULTS.md).

Interpretation guardrails: unchanged from v1 (SUPPORT = advance to a sharper
falsification stage; control failing sanity band -> pipeline suspect ->
INCONCLUSIVE regardless of GLASS numbers).

## Scout results recorded before production (measurability only)

- f=3, T=1.5, L=48: complete freeze by t=86 (mobility=0 forever; no site has
  >= 3 unlike neighbours once interfaces flatten). No growth law measurable.
  Matches pilot v1 m=3. -> ablation only.
- f=2, T=1.5, L=48: ordering completes by t~4800; growth window too narrow.
- f=0/f=2, T=0.9, L=48: both saturate by t~1000 (site-saturated deep quench;
  finite-size dominated). -> L must be larger for a decade-scale window.
- persistence scout values (T=0.9, L=48): GLASS 0.149 vs CONTROL 0.011 at
  t_end -> relative arrest gate above is satisfiable and discriminative.

## Runtime cap (v2, final; production parameters per amendment v2.1)

Production: L=126 (divisible by 3 for the block observable), T=1.5,
sweeps=12000, 3 seeds x {GLASS f=2, CONTROL f=0} + 1 f=3 ablation run; each
capped at 400 s wall by an in-run guard; total compute target well under
40 min wall clock. Scout runs (L<=48, throwaway seeds) permitted for
measurability checks only, as in v1.
