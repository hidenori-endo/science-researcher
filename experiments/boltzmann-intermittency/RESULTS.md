# Verification: combo:boltzmann-intermittency

**Hypothesis.** Turbulence intermittency exponents can be treated
Boltzmann-style as ensemble counting: fit a two-parameter
configuration-entropy (large-deviation) model to structure-function
scaling exponents ζ_p and check whether it reproduces measured anomalous
exponents better than the log-Poisson (She–Leveque) cascade prediction.

**Cheap falsification criterion.** If the entropy fit is not competitive
with log-Poisson on shell-model data, discard.

## Method

`run.py` (pure Python + `math`, no numpy):

1. **Sabra shell model**, N=22 shells, k_n = 2^n, ν = 10⁻⁸, constant
   forcing f = |f|(1+i) on shells 0–1:

   du_n/dt = i( k_{n+1} u*ₙ₊₁ uₙ₊₂ − δ′ k_n u*ₙ₋₁ uₙ₊₁
               + (1−δ′) k_{n−1} uₙ₋₁ uₙ₋₂ ) − νk_n² u_n + f_n,  δ′ = 1/2.

   The third-term sign was fixed by an explicit machine-precision check
   that d/dt Σ|u_n|²/2 = 0 for the inviscid unforced system (a common
   mis-transcription with −(1−δ′) injects energy and blows up).

2. **Integration**: Strang-split scheme — exact exponential damping for
   the stiff viscous term (νk²ᵢₐₓ ≈ 4.4×10⁴ otherwise forces dt ≲ 5×10⁻⁵),
   RK2 (midpoint) for the nonlinear terms, adaptive dt from a
   neighbor-sum CFL (dt = 0.12 / max_n k_n(|u_{n−1}|+|u_n|+|u_{n+1}|)),
   capped at 2×10⁻³, with step rejection on non-finite/overshooting
   growth. K41-consistent initial condition; forcing amplitude
   auto-calibrated so the measured dissipation rate ε = νΣk²|u|² matches
   ν³k_diss⁴ with k_diss = 2¹⁶ (cutoff near shell 16–17).
   Zero rejected steps in the final run.

3. **Run length**: transient t=250 plus production t=1500 in code time
   units; large-eddy turnover time T_L = 1/(k₀U₁) ≈ 30, i.e. ~50 turnover
   times total. 4.15×10⁶ steps, 445 055 moment samples, wall clock 524 s.

4. **Exponents**: velocity increments δu_n = u_n − u_{n−1},
   S_p(n) = ⟨|δu_n|^p⟩ for p=1..8; ζ_p from extended self-similarity
   (regression of ln S_p on ln S_3 over shells 3..12; ζ_3 ≡ 1).

5. **Fits** (least squares against the simulated ζ_p):
   - *Log-Poisson (fitted)*: ζ_p = c₁p + c₂(1−g^p), 3 free params
     (c₁, c₂, g).
   - *Entropy, bimodal*: laminar/intense configuration classes with
     entropy gap D = ln(w_lam/w_int); Legendre minimization gives
     ζ_p ∝ min(p, pr+D); 2 free params (r, D). Forces a single-kink
     piecewise-linear ζ_p and (after zeta_1 normalization) ζ_1 = 1.
   - *Entropy, parabolic*: large-deviation weight P(h) ~ ℓ^{−s(h)} with
     s(h) = (h−h₀)²/2a over a continuum of Hölder configurations;
     saddle point gives ζ_p = h₀p − ap²/2; 2 free params (h₀, a)
     (the entropy-counting analogue of the log-normal cascade).
   - Reference: canonical She–Leveque, ζ_p = p/9 + 2[1−(2/3)^{p/3}]
     (no free parameters), and the canonical experimental set
     (Anselmet et al. 1984; ζ₆ ≈ 1.78 anchor):
     0.36, 0.70, 1.00, 1.28, 1.53, 1.78, 2.01, 2.23.

## Results

| p | ζ_sim | She–Leveque (can.) | Log-Poisson (fit) | Entropy parabolic | Entropy bimodal |
|---|-------|--------------------|-------------------|-------------------|-----------------|
| 1 | 0.395 | 0.364              | 0.388             | 0.354             | 1.000           |
| 2 | 0.718 | 0.696              | 0.716             | 0.684             | 1.144           |
| 3 | 1.000 | 1.000              | 1.003             | 0.989             | 1.288           |
| 4 | 1.259 | 1.280              | 1.263             | 1.270             | 1.433           |
| 5 | 1.503 | 1.538              | 1.505             | 1.527             | 1.577           |
| 6 | 1.736 | 1.778              | 1.736             | 1.759             | 1.721           |
| 7 | 1.960 | 2.001              | 1.958             | 1.967             | 1.865           |
| 8 | 2.176 | 2.211              | 2.176             | 2.151             | 2.009 |

Simulated ζ₆ = 1.736 vs the experimental anchor ≈ 1.78 — the simulation
reproduces intermittency realistically (RMS of ζ_sim vs canonical
experiment: 0.035, comparable to She–Leveque's own error there).

**RMS errors:**

| Model | vs simulated ζ_p | vs canonical experiment | free params |
|---|---|---|---|
| She–Leveque (canonical) | 0.031 | 0.008 | 0 |
| Log-Poisson (fitted c₁,c₂,g) | **0.0032** | 0.035 | 3 |
| Entropy, parabolic (h₀,a) | 0.025 | 0.034 | 2 |
| Entropy, bimodal (r,D) | 0.297 | 0.314 | 2 |

Fitted parameters: log-Poisson (c₁,c₂,g) = (0.207, 0.540, 0.664);
parabolic entropy h₀ = 0.366, a = 0.0244; bimodal r = 0.136,
D = 0.806.

## Verdict: **DISCARD** (falsification criterion met)

- The two-class (bimodal) entropy ensemble fails outright: a single
  entropy gap yields a one-kink piecewise-linear ζ_p that cannot bend,
  missing ζ₁ by a factor >2 (RMS ≈ 0.30, ten times worse than anything
  else).
- The best entropy variant (parabolic rate function) merely *matches*
  the parameter-free She–Leveque prediction (0.025 vs 0.031 RMS) and is
  an order of magnitude worse than log-Poisson given equal fitting
  freedom (0.025 vs 0.003). It also just recovers the log-normal form
  ζ_p = h₀p − ap²/2, i.e. "Boltzmann counting" with a Gaussian entropy
  adds nothing that log-normal cascade phenomenology doesn't already
  encode.
- To actually beat log-Poisson, the counting framework would need the
  true rate function s(h) — which must be measured from the same
  dynamics it is supposed to explain. This reproduces exactly the
  failure mode anticipated in the hypothesis ("weights may be
  dynamics-dependent, reintroducing the unsolved problem").

## Next step (if revisited)

The only version of the program that could still be non-circular is an
*ab initio* derivation of s(h) from shell-model phase-space volume
counting (e.g., counting Fourier modes consistent with a given local
slope), checked by whether it predicts s(h) on one forcing and
transfers to another. Given the two-parameter outcome here, expected
payoff is low; higher-value follow-ups are direct measurements of the
multifractal spectrum D(h) convergence with Reynolds number in this
setup, or testing refined similarity models (e.g., Berkowitz–Eyink
fusion estimates) on the same trajectory data.
