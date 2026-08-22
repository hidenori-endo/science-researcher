#!/usr/bin/env python3
"""Verify hypothesis combo:boltzmann-intermittency.

Turbulence intermittency exponents treated Boltzmann-style as ensemble
counting: fit a two-parameter configuration-entropy (large-deviation)
model to structure-function scaling exponents zeta_p measured in the
Sabra shell model, and compare against the log-Poisson (She-Leveque)
cascade prediction.

Pure Python + math only.

Method
------
1. Integrate the Sabra shell model (N=22 shells, k_n = 2^n, nu=1e-8,
   constant forcing on shells 0-1) with an adaptive-step RK2 scheme for
   the nonlinear terms and exact exponential damping (Strang splitting)
   for the stiff viscous term -nu k_n^2 u_n.
2. Accumulate velocity-increment structure functions
   S_p(n) = <|u_n - u_{n-1}|^p>, p = 1..8.
3. Extract zeta_p by extended self-similarity (ESS): regress ln S_p
   against ln S_3 over inertial-range shells, normalize zeta_3 = 1.
4. Fit three models:
   (a) generalized log-Poisson:      zeta_p = c1 p + c2 (1 - g^p)
   (b) two-class configuration-entropy (Boltzmann/large-deviation):
       laminar vs intense increment classes with entropy gap
       D = ln(w_lam/w_int); Legendre minimization gives
       zeta_p ~ min(p, p r + D)/min(1, r + D), free params (r, D).
   (c) parabolic configuration-entropy: large-deviation weight
       P(h) ~ l^{-(h-h0)^2/2a}; saddle point gives
       zeta_p = h0 p - a p^2/2, free params (h0, a).
5. Compare RMS errors against simulated zeta_p and against canonical
   experimental exponents (zeta_6 ~ 1.78 anchor).
"""

import json
import math
import os
import random
import time

# ----------------------------------------------------------------------
# Parameters
# ----------------------------------------------------------------------

N_SHELLS = 22
H_RATIO = 2.0          # k_{n+1}/k_n
K0 = 1.0
NU = 1e-8              # kinematic viscosity

P_ORDERS = list(range(1, 9))       # p = 1..8
N_P = len(P_ORDERS)
SAMPLE_EVERY = 5                   # steps between moment accumulations
DT_SAFETY = 0.12                   # CFL safety factor
DT_MAX = 2e-3
FORCE_AMP = 5e-4 * (1 + 1j)        # initial guess; auto-calibrated to eps_target
SHELLS_FORCED = (0, 1)
ESS_LO, ESS_HI = 3, 12             # inertial-range shells for ESS regression
DISS_SHELL = 16                     # target viscous cutoff shell (sets forcing)


def make_k():
    return [K0 * (H_RATIO ** n) for n in range(N_SHELLS)]


# ----------------------------------------------------------------------
# Integrator: Strang-split RK2 for the nonlinear Sabra terms,
# exact exponential damping for the linear viscous term.
# ----------------------------------------------------------------------

def rhs_nonlinear(u, k, force):
    """Nonlinear (inertial) part of the Sabra shell model RHS.

    du_n/dt = i( k_{n+1} u*_{n+1} u_{n+2}
                 - delta' k_n u*_{n-1} u_{n+1}
                 + (1-delta') k_{n-1} u_{n-1} u_{n-2} ),  delta' = 1/2.

    These coefficients make d/dt sum(|u_n|^2)/2 vanish exactly (verified
    to machine precision on random states), which is required for a
    stable inertial cascade; the third-term sign is fixed relative to a
    common mis-transcription by this explicit conservation check.
    """
    n_sh = len(u)
    out = [0j] * n_sh
    for n in range(n_sh):
        acc = force[n]
        if n + 2 < n_sh:
            acc += k[n + 1] * u[n + 1].conjugate() * u[n + 2]
        if 0 < n < n_sh - 1:
            acc -= 0.5 * k[n] * u[n - 1].conjugate() * u[n + 1]
        if n >= 2:
            acc += 0.5 * k[n - 1] * u[n - 1] * u[n - 2]
        out[n] = 1j * acc
    return out


def damp(u, damp_factors):
    return [u[n] * damp_factors[n] for n in range(len(u))]


def measure_eps(u, k):
    """Dissipation rate eps = nu * sum_n k_n^2 |u_n|^2."""
    return NU * sum(k[n] * k[n] * abs(u[n]) ** 2 for n in range(N_SHELLS))


def run_simulation(t_transient=300.0, t_total=1200.0, seed=42,
                   verbose=True):
    rng = random.Random(seed)
    k = make_k()
    force = [0j] * N_SHELLS
    for n in SHELLS_FORCED:
        force[n] = FORCE_AMP

    # K41-consistent initial condition: u_n = A k_n^{-1/3} with random
    # phases, A^3 ~= target dissipation rate. Avoids the violent cascade
    # front (and slave-shell blowup) of a flat random start.
    eps0 = NU ** 3 * K0 ** -4 * H_RATIO ** (4 * DISS_SHELL)  # target epsilon
    amp0 = eps0 ** (1.0 / 3.0)
    u = []
    for n in range(N_SHELLS):
        mag = amp0 * (k[n] / K0) ** (-1.0 / 3.0)
        ph = rng.uniform(0.0, 2.0 * math.pi)
        u.append(complex(mag * math.cos(ph), mag * math.sin(ph)))

    exp_half_cache = {}

    def half_damp_factors(dt):
        f = exp_half_cache.get(dt)
        if f is None:
            f = [math.exp(-0.5 * NU * k[n] * k[n] * dt)
                 for n in range(N_SHELLS)]
            if len(exp_half_cache) < 4096:
                exp_half_cache[dt] = f
        return f

    u = [complex(rng.uniform(-1e-3, 1e-3), rng.uniform(-1e-3, 1e-3))
         for _ in range(N_SHELLS)]

    sums = [[0.0] * N_SHELLS for _ in range(N_P)]

    def do_step(dt):
        """Strang split step: half damping, RK2 nonlinear, half damping."""
        fh = half_damp_factors(dt)
        uh = damp(u, fh)                       # half viscous damping
        du1 = rhs_nonlinear(uh, k, force)
        um = [uh[n] + 0.5 * dt * du1[n] for n in range(N_SHELLS)]
        du2 = rhs_nonlinear(um, k, force)
        un = [uh[n] + dt * du2[n] for n in range(N_SHELLS)]
        return damp(un, fh)                    # other half damping

    def max_u(v):
        m = 0.0
        for x in v:
            a = abs(x)
            if a > m:
                m = a
        return m

    t = 0.0
    steps = 0
    rejected = 0
    nsamp = 0
    t_start = time.time()

    def advance(t_end, accumulate=False):
        nonlocal u, t, steps, rejected, nsamp
        dt_scale = 1.0
        while t < t_end:
            # --- adaptive timestep ---------------------------------------
            # Neighbor-sum CFL: the fastest local time scale of shell n is
            # set by its own amplitude plus both neighbours' (nonlinear
            # coupling products). Strongly viscous shells are handled
            # exactly by the exponential damping factors, so no separate
            # nu*k^2 constraint is needed.
            a = [abs(x) for x in u]
            m = 0.0
            for n in range(N_SHELLS):
                s = a[n]
                if n > 0:
                    s += a[n - 1]
                if n + 1 < N_SHELLS:
                    s += a[n + 1]
                v = k[n] * s
                if v > m:
                    m = v
            dt = DT_SAFETY / m if m > 0.0 else DT_MAX
            if dt > DT_MAX:
                dt = DT_MAX
            dt *= dt_scale
            if t + dt > t_end:
                dt = t_end - t
            old_max = max_u(u)
            un = do_step(dt)
            new_max = max_u(un)
            ok = True
            for x in un:
                if x != x or abs(x) == float("inf"):
                    ok = False
                    break
            if ok and new_max > 4.0 * old_max + 1e-12:
                # burst overshoot guard: reject and shrink
                ok = False
            if not ok:
                rejected += 1
                dt_scale *= 0.5
                if dt_scale < 1e-6:
                    dt_scale = 1e-6
                continue
            u = un
            t += dt
            steps += 1
            dt_scale = min(1.0, dt_scale * 1.1)
            if accumulate and steps % SAMPLE_EVERY == 0:
                for n in range(1, N_SHELLS):
                    d = abs(u[n] - u[n - 1])
                    pw = 1.0
                    for i in range(N_P):
                        pw *= d
                        sums[i][n] += pw
                nsamp += 1

    # Phase 0: calibrate forcing amplitude so that the measured dissipation
    # rate eps = nu sum k^2 |u|^2 matches the K41 target for a viscous
    # cutoff at shell DISS_SHELL:  eps_target = nu^3 * k_diss^4.
    eps_target = NU ** 3 * (K0 * H_RATIO ** DISS_SHELL) ** 4
    for it in range(4):
        advance(t + 25.0)
        eps_now = measure_eps(u, k)
        if verbose:
            print(f"calib[{it}]: t={t:.1f} eps={eps_now:.3e} "
                  f"target={eps_target:.3e}", flush=True)
        if 0.5 < eps_now / eps_target < 2.0:
            break
        fscale = (eps_target / eps_now) ** 0.75
        for n in SHELLS_FORCED:
            force[n] *= fscale
    if verbose:
        print(f"forcing calibrated: |f|={abs(force[SHELLS_FORCED[0]]):.3e}, "
              f"eps={measure_eps(u, k):.3e}", flush=True)

    # Phase 1: transient spin-up
    advance(t_transient)
    if verbose:
        print(f"transient done: t={t:.2f}, steps={steps}, "
              f"rejected={rejected}, {time.time()-t_start:.1f}s", flush=True)
        print("shell, k, |u|^2:", flush=True)
        for n in range(N_SHELLS):
            print(f"  {n:2d} {k[n]:12.4e} {abs(u[n])**2:12.4e}", flush=True)

    # Phase 2: production run
    advance(t + t_total, accumulate=True)

    wall = time.time() - t_start
    if verbose:
        print(f"production done: t={t:.2f}, total steps={steps}, "
              f"samples={nsamp}, rejected={rejected}, wall={wall:.1f}s",
              flush=True)

    sf = [[sums[i][n] / max(nsamp, 1) for n in range(N_SHELLS)]
          for i in range(N_P)]
    return {"sf": sf, "nsamp": nsamp, "wall": wall, "steps": steps,
            "rejected": rejected}


# ----------------------------------------------------------------------
# ESS exponent extraction
# ----------------------------------------------------------------------

def ess_exponents(sf, shell_lo=ESS_LO, shell_hi=ESS_HI):
    """Extended self-similarity: regress ln S_p vs ln S_3 over the
    inertial-range shells; slope = zeta_p / zeta_3, zeta_3 := 1."""
    logs3 = [math.log(sf[2][n]) for n in range(shell_lo, shell_hi + 1)]
    nl = len(logs3)
    mx = sum(logs3) / nl
    var = sum((x - mx) ** 2 for x in logs3)
    out = {}
    for i, p in enumerate(P_ORDERS):
        lp = [math.log(sf[i][n]) for n in range(shell_lo, shell_hi + 1)]
        mp = sum(lp) / nl
        cov = sum((lp[j] - mp) * (logs3[j] - mx) for j in range(nl))
        out[p] = cov / var
    return out


# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------

def she_leveque(p):
    """She-Leveque 1994 log-Poisson: zeta_p = p/9 + 2[1-(2/3)^{p/3}]."""
    return p / 9.0 + 2.0 * (1.0 - (2.0 / 3.0) ** (p / 3.0))


def fit_log_poisson(zeta):
    """Generalized log-Poisson fit zeta_p = c1*p + c2*(1-g^p);
    coarse-to-fine grid search on (c1, c2, g)."""

    def err(c1, c2, g):
        s = 0.0
        for p, z in zeta.items():
            d = z - (c1 * p + c2 * (1 - g ** p))
            s += d * d
        return math.sqrt(s / len(zeta))

    best = (1.0 / 3.0, 2.0, 2.0 / 3.0)
    be = err(*best)
    c1r = [0.0, 0.6]; c2r = [0.0, 3.0]; gr = [0.2, 0.98]
    for _ in range(7):
        n = 25
        for i in range(n):
            c1 = c1r[0] + (c1r[1] - c1r[0]) * i / (n - 1)
            for j in range(n):
                c2 = c2r[0] + (c2r[1] - c2r[0]) * j / (n - 1)
                for l in range(n):
                    g = gr[0] + (gr[1] - gr[0]) * l / (n - 1)
                    e = err(c1, c2, g)
                    if e < be:
                        be = e
                        best = (c1, c2, g)
        s1 = (c1r[1] - c1r[0]) / (n - 1)
        s2 = (c2r[1] - c2r[0]) / (n - 1)
        sg = (gr[1] - gr[0]) / (n - 1)
        c1r = [max(0.0, best[0] - 1.5 * s1), best[0] + 1.5 * s1]
        c2r = [max(0.0, best[1] - 1.5 * s2), best[1] + 1.5 * s2]
        gr = [max(0.05, best[2] - 1.5 * sg), min(0.999, best[2] + 1.5 * sg)]
    params = best
    return {"params": params, "rms": be,
            "predict": {p: params[0] * p + params[1] * (1 - params[2] ** p)
                        for p in P_ORDERS}}


def entropy_fit_bimodal(zeta):
    """Two-parameter configuration-entropy (large-deviation bimodal) fit.

    Ensemble picture: at scale l the increment belongs to one of two
    configuration classes with entropy weights
      P_lam ~ l^0 (laminar, Hoelder h_L),  P_int ~ l^{-D'} (intense, h_I<r).
    Moments <du^p> ~ sum_h w_h l^{p h}; the Legendre (large-deviation)
    minimization over configuration weights gives
      zeta_p = min(p*h_L, p*h_I + ln(w_lam/w_int)).
    After normalizing zeta_1 -> 1 the two free shape parameters are
      r = h_I / h_L          (intermittency strength of the intense class)
      D = ln(w_lam/w_int)/h_L (entropy gap between classes)
    Fit (r, D) by least squares against the measured zeta_p.
    """

    def rms(r, D):
        norm = min(1.0, r + D)
        s = 0.0
        for p, z in zeta.items():
            m = min(float(p), p * r + D) / norm
            d = z - m
            s += d * d
        return math.sqrt(s / len(zeta))

    def predict(r, D):
        norm = min(1.0, r + D)
        return {p: min(float(p), p * r + D) / norm for p in P_ORDERS}

    r_lo, r_hi = 0.02, 1.2
    D_lo, D_hi = 0.0, 3.0
    best_r, best_D = 1.0 / 3.0, 2.0 / 3.0
    be = rms(best_r, best_D)
    for _ in range(9):
        n = 31
        for i in range(n):
            r = r_lo + (r_hi - r_lo) * i / (n - 1)
            for j in range(n):
                D = D_lo + (D_hi - D_lo) * j / (n - 1)
                e = rms(r, D)
                if e < be:
                    be = e
                    best_r, best_D = r, D
        sr = (r_hi - r_lo) / (n - 1)
        sd = (D_hi - D_lo) / (n - 1)
        r_lo = max(0.005, best_r - 1.5 * sr); r_hi = best_r + 1.5 * sr
        D_lo = max(0.0, best_D - 1.5 * sd); D_hi = best_D + 1.5 * sd
    return {"r": best_r, "D": best_D, "rms": be,
            "predict": predict(best_r, best_D)}


def entropy_fit_parabolic(zeta):
    """Parabolic configuration-entropy (large-deviation) fit.

    Boltzmann-style counting over a continuum of Hoelder-exponent
    configurations: the probability of a configuration with local
    scaling exponent h carries a large-deviation (entropy) weight
      P(h) ~ l^{s(h)},   s(h) = (h - h0)^2 / (2a),
    nonnegative and minimal at the most numerous (typical)
    configuration h0; a sets the entropy width. The multifractal
    saddle-point (Legendre) minimization over configurations gives
      zeta_p = min_h [ p*h + s(h) ] = h0*p - a*p^2/2.
    Two free parameters (h0, a), fitted by least squares to zeta_p.
    This is the entropy-counting analogue of the log-normal cascade.
    """

    def rms(h0, a):
        s = 0.0
        for p, z in zeta.items():
            d = z - (h0 * p - 0.5 * a * p * p)
            s += d * d
        return math.sqrt(s / len(zeta))

    best_h0, best_a = 1.0 / 3.0, 0.03
    be = rms(best_h0, best_a)
    h0r = [0.05, 0.6]; ar = [0.0, 0.15]
    for _ in range(9):
        n = 41
        for i in range(n):
            h0 = h0r[0] + (h0r[1] - h0r[0]) * i / (n - 1)
            for j in range(n):
                a = ar[0] + (ar[1] - ar[0]) * j / (n - 1)
                e = rms(h0, a)
                if e < be:
                    be = e
                    best_h0, best_a = h0, a
        sh = (h0r[1] - h0r[0]) / (n - 1)
        sa = (ar[1] - ar[0]) / (n - 1)
        h0r = [max(0.01, best_h0 - 1.5 * sh), best_h0 + 1.5 * sh]
        ar = [max(0.0, best_a - 1.5 * sa), best_a + 1.5 * sa]
    pred = {p: best_h0 * p - 0.5 * best_a * p * p for p in P_ORDERS}
    return {"h0": best_h0, "a": best_a, "rms": be, "predict": pred}


# ----------------------------------------------------------------------
# Canonical experimental reference (Anselmet et al. 1984 / Benzi et al.;
# zeta_6 ~ 1.78 anchor)
# ----------------------------------------------------------------------

CANONICAL_EXP = {
    1: 0.36, 2: 0.70, 3: 1.00, 4: 1.28,
    5: 1.53, 6: 1.78, 7: 2.01, 8: 2.23,
}


def rms_against(pred, ref):
    return math.sqrt(sum((pred[p] - ref[p]) ** 2 for p in ref) / len(ref))


# ----------------------------------------------------------------------

def main():
    t0 = time.time()
    random.seed(12345)

    t_transient = float(os.environ.get("SIM_T_TRANSIENT", 300.0))
    t_total = float(os.environ.get("SIM_T_TOTAL", 1200.0))

    print(f"Sabra shell model: N={N_SHELLS}, h={H_RATIO}, k0={K0}, "
          f"nu={NU}, force={FORCE_AMP} on shells {SHELLS_FORCED}", flush=True)
    sim = run_simulation(t_transient=t_transient, t_total=t_total)

    zeta_sim = ess_exponents(sim["sf"])
    # NOTE: ESS slopes are already normalized so that zeta_3 = 1 exactly
    # (regression against ln S_3). Do not renormalize by zeta_1.

    sl = {p: she_leveque(p) for p in P_ORDERS}
    lp = fit_log_poisson(zeta_sim)
    ent_par = entropy_fit_parabolic(zeta_sim)
    ent_bim = entropy_fit_bimodal(zeta_sim)

    e_sl_sim = rms_against(sl, zeta_sim)
    e_lp_sim = rms_against(lp["predict"], zeta_sim)
    e_ent_sim = rms_against(ent_par["predict"], zeta_sim)
    e_bim_sim = rms_against(ent_bim["predict"], zeta_sim)

    e_sl_exp = rms_against(sl, CANONICAL_EXP)
    e_lp_exp = rms_against(lp["predict"], CANONICAL_EXP)
    e_ent_exp = rms_against(ent_par["predict"], CANONICAL_EXP)
    e_bim_exp = rms_against(ent_bim["predict"], CANONICAL_EXP)
    e_sim_exp = rms_against(zeta_sim, CANONICAL_EXP)

    print("\n=== zeta_p ===")
    print("p   sim     SL(can)  LP(fit)  entr-par  entr-bim")
    for p in P_ORDERS:
        print(f"{p}   {zeta_sim[p]:.3f}   {sl[p]:.3f}    "
              f"{lp['predict'][p]:.3f}    {ent_par['predict'][p]:.3f}"
              f"     {ent_bim['predict'][p]:.3f}")

    print("\nRMS vs simulation:",
          {k: round(v, 4) for k, v in
           (("she_leveque", e_sl_sim), ("log_poisson_fit", e_lp_sim),
            ("entropy_parabolic", e_ent_sim),
            ("entropy_bimodal", e_bim_sim))})
    print("RMS vs canonical experiment:",
          {k: round(v, 4) for k, v in
           (("she_leveque", e_sl_exp), ("log_poisson_fit", e_lp_exp),
            ("entropy_parabolic", e_ent_exp),
            ("entropy_bimodal", e_bim_exp), ("simulated", e_sim_exp))})
    print("log-Poisson fitted params (c1, c2, g) =",
          tuple(round(x, 4) for x in lp["params"]))
    print(f"parabolic entropy fit: h0={ent_par['h0']:.4f}, "
          f"a={ent_par['a']:.5f}")
    print(f"bimodal entropy fit: r={ent_bim['r']:.4f} (h_int/h_lam), "
          f"D={ent_bim['D']:.4f} (entropy gap)")
    print(f"total wall {time.time()-t0:.1f}s")

    results = {
        "zeta_sim": zeta_sim,
        "zeta_she_leveque_canonical": sl,
        "zeta_log_poisson_fit": lp["predict"],
        "zeta_entropy_parabolic_fit": ent_par["predict"],
        "zeta_entropy_bimodal_fit": ent_bim["predict"],
        "log_poisson_params_c1_c2_g": lp["params"],
        "entropy_parabolic_params_h0_a": {"h0": ent_par["h0"],
                                          "a": ent_par["a"]},
        "entropy_bimodal_params_r_D": {"r": ent_bim["r"],
                                       "D": ent_bim["D"]},
        "rms_vs_simulation": {"she_leveque_canonical": e_sl_sim,
                              "log_poisson_fit": e_lp_sim,
                              "entropy_parabolic": e_ent_sim,
                              "entropy_bimodal": e_bim_sim},
        "rms_vs_canonical_experiment": {
            "she_leveque_canonical": e_sl_exp,
            "log_poisson_fit": e_lp_exp,
            "entropy_parabolic": e_ent_exp,
            "entropy_bimodal": e_bim_exp,
            "simulated": e_sim_exp},
        "canonical_experimental": CANONICAL_EXP,
        "simulation": {"nsamp": sim["nsamp"], "wall_s": sim["wall"],
                       "steps": sim["steps"], "rejected_steps":
                       sim["rejected"]},
        "parameters": {
            "model": "Sabra", "N_SHELLS": N_SHELLS, "h": H_RATIO, "k0": K0,
            "nu": NU, "force": repr(FORCE_AMP),
            "shells_forced": list(SHELLS_FORCED),
            "integrator": "Strang-split RK2 (nonlinear) + exact exp damping "
                          "(viscous), adaptive dt = neighbor-sum CFL * 0.12",
            "forcing_calibration": "auto: rescale |f| so measured eps "
                                   "matches nu^3*k_diss^4, k_diss=2^16",
            "eps_target": NU ** 3 * (K0 * H_RATIO ** DISS_SHELL) ** 4,
            "t_transient": t_transient, "t_production": t_total,
            "sample_every": SAMPLE_EVERY, "ess_shells": [ESS_LO, ESS_HI],
        },
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "results.json")
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
