"""Classic template-based linear invariant generator (the baseline).

Implements exactly what stage 1's "translation duality" reduces to: affine
templates q(x) = ell.x + c solved exactly against every branch.

Two variants:
  conserved (primary): q(f_b(x)) - q(x) == 0 identically on every branch
      => ell.(A_b - I) = 0 and ell.b_b = 0, one homogeneous linear system
      over Q solved by exact Gaussian elimination.
  eigen (secondary, reported for transparency): multiplicative templates
      q(f_b(x)) == lambda * q(x) with a common rational lambda from the same
      small-rational list the symmetry engine probes, requiring ell.b_b = 0
      and level set through init (k = 0), i.e. linear eigenforms of the
      transition maps -- NOT part of the headline baseline.

Claims are validated with the same machinery as the symmetry engine
(validate_candidate + is_nontrivial + mutated-variable filter), so both
methods run under identical acceptance rules and parse filters.
"""

from fractions import Fraction

from engine import lin, pstr, simulate
from symmetry import nullspace, validate_candidate, is_nontrivial

# small-rational multiplicative-template probes (linear eigenforms)
LAMBDAS = ([Fraction(s * d) for s in (1, -1) for d in
            (1, 2, 3, 4, 6, 8, 9, 12, 16, 27, 81)] +
           [Fraction(s, d) for s in (1, -1) for d in
            (2, 3, 4, 6, 8, 9, 16, 27, 81)] +
           [Fraction(2, 3), Fraction(3, 2), Fraction(4, 3),
            Fraction(3, 4)])


def _affine_parts(lp):
    """Extract A_b (rows x cols as list of lists) and b_b per branch, or None
    if some update is not affine."""
    parts = []
    for _, upd in lp.branches:
        A = [[Fraction(0)] * lp.n for _ in range(lp.n)]
        b = [Fraction(0)] * lp.n
        for v in range(lp.n):
            p = upd.get(v, lin(lp.n, {v: 1}))
            for m, c in p.items():
                m = m + (0,) * max(0, lp.n - len(m))
                if sum(m) == 0:
                    b[v] += c
                elif sum(m) == 1:
                    i = next(i for i, e in enumerate(m) if e)
                    if m[i] != 1:
                        return None
                    A[v][i] += c
                else:
                    return None
        parts.append((A, b))
    return parts


def _claims_from_ells(lp, ells, reached):
    claims = []
    for ell in ells:
        poly = lin(lp.n, {i: Fraction(c) for i, c in enumerate(ell) if c != 0})
        if not poly:
            continue
        claim = validate_candidate(lp, poly, reached)
        if claim and is_nontrivial(lp, claim["poly"]):
            touched = set()
            for m, c in claim["poly"].items():
                for i, e in enumerate(m + (0,) * max(0, lp.n - len(m))):
                    if e:
                        touched.add(i)
            if touched & lp.mutated:
                claims.append(claim)
    return claims


def run_baseline(lp, include_eigen=False):
    """Conserved affine-template solving. Returns dict with claims."""
    parts = _affine_parts(lp)
    if parts is None:
        return {"claims": [], "n_templates": 0,
                "reason": "non-affine updates"}
    rows = []
    for A, b in parts:
        # ell.(A - I) = 0  ->  column j of constraint matrix: sum_v ell_v (A[v][j] - delta_vj)
        for j in range(lp.n):
            rows.append([A[v][j] - (Fraction(1) if v == j else Fraction(0))
                         for v in range(lp.n)])
        rows.append(list(b))
    ns = nullspace(rows) if rows else None
    claims = _claims_from_ells(lp, ns or [], simulate(lp))

    eig_claims = []
    if include_eigen and ns is not None:
        reached = simulate(lp)
        for lam in LAMBDAS:
            rows2 = []
            ok = True
            for A, b in parts:
                # ell.A = lambda * ell   and   ell.b = 0 (level set through init)
                for j in range(lp.n):
                    rows2.append([A[v][j] - (lam if v == j else Fraction(0))
                                  for v in range(lp.n)])
                rows2.append(list(b))
            ns2 = nullspace(rows2)
            eig_claims.extend(_claims_from_ells(lp, ns2 or [], reached))

    return {"claims": claims, "eigen_claims": eig_claims,
            "n_templates": len(ns or []),
            "reason": None}
