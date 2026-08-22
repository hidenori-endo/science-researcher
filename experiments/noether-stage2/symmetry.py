"""Stage-1 Noether symmetry engine, ported to CLoop inputs.

Pipeline per loop (identical machinery to experiments/noether-loop-invariants/
run.py, minus the annotated-target entailment step, which has no counterpart
on real SV-COMP sources):

  1. symmetry detection: homogeneous linear transforms T: x_i -> c*x_sigma(i)
     searched for automorphisms of the transition relation (exact poly
     identity T o f == f o T on every branch);
  2. finite-symmetry eigenforms on the degree-<=2 monomial basis (exact
     rational nullspaces of M - lambda*I), plus same-lambda sums/differences;
  3. translation duality for pure-translation branch systems;
  4. inductive validation: exact polynomial identity checks + numeric sanity
     over simulated reachable states.

strict mode   : finite-automorphism eigenforms only
extended mode : finite + translation duality
"""

import random
from fractions import Fraction

from engine import (CLoop, padd, pneg, psub, pscale, peval, pident, pstr,
                    lin, simulate, substitute, degree)

# ---------------------------------------------------------------- helpers


def nullspace(rows):
    if not rows:
        return None
    m, n = len(rows), len(rows[0])
    a = [list(map(Fraction, r)) for r in rows]
    pivots = []
    r = 0
    for c in range(n):
        pr = next((i for i in range(r, m) if a[i][c] != 0), None)
        if pr is None:
            continue
        a[r], a[pr] = a[pr], a[r]
        pv = a[r][c]
        a[r] = [x / pv for x in a[r]]
        for i in range(m):
            if i != r and a[i][c] != 0:
                f = a[i][c]
                a[i] = [x - f * y for x, y in zip(a[i], a[r])]
        pivots.append(c)
        r += 1
        if r == m:
            break
    free = [c for c in range(n) if c not in pivots]
    basis = []
    for fc in free:
        v = [Fraction(0)] * n
        v[fc] = Fraction(1)
        for i, pc in enumerate(pivots):
            v[pc] = -a[i][fc]
        basis.append(tuple(v))
    return basis


def normalize_vec(v):
    nz = next((x for x in v if x != 0), None)
    if nz is None:
        return None
    w = tuple(x / nz for x in v)
    if next(x for x in w if x != 0) < 0:
        w = tuple(-x for x in w)
    return w


# ------------------------------------------------------ symmetry detection

COEFS_FULL = [Fraction(1), Fraction(-1), Fraction(2), Fraction(-2),
              Fraction(3), Fraction(-3), Fraction(4), Fraction(-4),
              Fraction(9), Fraction(-9)]
COEFS_MID = [Fraction(1), Fraction(-1), Fraction(2), Fraction(-2)]
COEFS_SMALL = [Fraction(1), Fraction(-1)]


def coef_set(n):
    """Coefficient budget shrinks with dimension to keep the search finite
    (same trade-off as stage 1's COEFS / COEFS_BIG_N)."""
    if n <= 2:
        return COEFS_FULL
    if n <= 4:
        return COEFS_MID
    return COEFS_SMALL


def enumerate_transforms(n):
    from itertools import permutations, product as iproduct
    perms = list(permutations(range(n)))
    coefs = coef_set(n)
    for perm in perms:
        for choice in iproduct(coefs, repeat=n):
            if perm == tuple(range(n)) and all(c == 1 for c in choice):
                continue
            image = {i: {tuple(1 if j == perm[i] else 0 for j in range(n)):
                         choice[i]}
                     for i in range(n)}
            yield image


def commutes(lp, image):
    for _, upd in lp.branches:
        lhs = {v: substitute(u, image) for v, u in upd.items()}
        rhs = {v: substitute(image[v], upd) for v in range(lp.n)}
        for v in range(lp.n):
            if not pident(lhs[v], rhs[v]):
                return False
    return True


def detect_symmetries(lp):
    if lp.n >= 6:
        return []                   # search space explodes; recorded as skip
    return [image for image in enumerate_transforms(lp.n) if commutes(lp,
                                                                      image)]


# --------------------------------------------- finite-symmetry eigenforms
#
# A homogeneous monomial map T: x_i -> c_i * x_sigma(i) acts on the degree-<=2
# monomial basis by mapping monomials to SCALAR x monomial. Hence the induced
# matrix M is a permutation-scaling matrix; its rational eigenvalues are the
# cycle products of the basis-orbit map (prod over a cycle of length L has
# eigenvalues = L-th roots of prod; only rational ones matter). This replaces
# stage 1's fixed small-rational lambda probe with an EXACT per-image
# computation and keeps the cost bounded for larger state vectors.

MAX_IMAGES_FOR_EIGEN = 64          # cap eigenform extractions per loop


def monomial_basis(n, maxdeg=2):
    from itertools import product as iproduct
    basis = [m for m in iproduct(range(maxdeg + 1), repeat=n)
             if sum(m) <= maxdeg]
    return sorted(basis, key=lambda m: (sum(m), m))


def _integer_root(v, k):
    """Largest integer r with r**k == v (v > 0), else None."""
    r = round(v ** (1.0 / k))
    for cand in (r - 1, r, r + 1):
        if cand > 0 and cand ** k == v:
            return cand
    return None


def eigen_candidates(lp, image, maxdeg=2):
    """Eigenforms q (deg <= maxdeg) of one transformation T, via exact cycle
    decomposition of the induced basis map."""
    basis = monomial_basis(lp.n, maxdeg)
    index = {m: i for i, m in enumerate(basis)}
    dim = len(basis)

    def T_monomial(m):
        coef = Fraction(1)
        exp = [0] * lp.n
        for i, e in enumerate(m):
            if e:
                img = image[i]
                (me,), (mc,) = list(img.keys()), list(img.values())
                coef *= mc ** e
                for j in range(lp.n):
                    exp[j] += me[j] * e
        exp = tuple(exp)
        return coef, exp if exp in index else None

    tmap = {}
    for m in basis:
        coef, tm = T_monomial(m)
        if tm is None:                 # leaves the bounded-degree basis
            return []
        tmap[m] = (coef, tm)

    # cycle decomposition
    seen = set()
    lambdas = set()
    for m0 in basis:
        if m0 in seen:
            continue
        cycle = [m0]
        cur = tmap[m0][1]
        while cur != m0:
            if cur in seen or cur in cycle:
                break
            cycle.append(cur)
            cur = tmap[cur][1]
        seen.update(cycle)
        if cur != m0:
            continue
        L = len(cycle)
        prod = Fraction(1)
        for m in cycle:
            prod *= tmap[m][0]
        # lam^L == prod, lam rational
        num, den = prod.numerator, prod.denominator
        rn = _integer_root(num, L) if num > 0 else (
            -_integer_root(-num, L) if L % 2 == 1 else None)
        rd = _integer_root(den, L)
        if rn is None or rd is None:
            continue
        lam = Fraction(rn, rd)
        if lam ** L != prod:
            continue
        lambdas.add(lam)
        if L % 2 == 0 and (-lam) ** L == prod:
            lambdas.add(-lam)

    rowsM = [[Fraction(0)] * dim for _ in range(dim)]
    for j, m in enumerate(basis):
        coef, tm = tmap[m]
        rowsM[index[tm]][j] += coef

    out = []
    for lam in sorted(lambdas):
        rows = [[rowsM[i][j] - (lam if i == j else 0) for j in range(dim)]
                for i in range(dim)]
        ns = nullspace(rows)
        if not ns:
            continue
        for vec in ns:
            nv = normalize_vec(vec)
            if nv is None:
                continue
            poly = {m: c for m, c in zip(basis, nv) if c != 0}
            out.append((lam, poly))
    return out


# ------------------------------------------ translation duality

def translation_candidates(lp):
    deltas = []
    for _, upd in lp.branches:
        d = []
        for v in range(lp.n):
            diff = padd(upd.get(v, lin(lp.n, {v: 1})),
                        pneg(lin(lp.n, {v: 1})))
            if any(sum(m) >= 1 for m in diff):
                return []          # not a pure translation on this branch
            d.append(sum(c for m, c in diff.items()
                         if all(e == 0 for e in m)))
        deltas.append(d)
    ns = nullspace(deltas)         # rows: ell . Delta_b = 0
    out = []
    for vec in ns or []:
        poly = lin(lp.n, {i: int(c) if c == int(c) else c
                          for i, c in enumerate(vec) if c != 0})
        out.append(poly)
    return out


# ------------------------------------------------------- validation

def infer_kappa(g, q, lp):
    rng = random.Random(20260821)
    for _ in range(8):
        pt = [rng.randint(-20, 20) for _ in range(lp.n)]
        qv = peval(q, pt)
        if qv != 0:
            kappa = peval(g, pt) / qv
            return kappa if pident(g, pscale(q, kappa)) else None
    return None


def validate_candidate(lp, q, reached):
    k = peval(q, lp.init)
    covariant = False
    for _, upd in lp.branches:
        g = substitute(q, upd)
        if pident(g, q):
            continue
        kappa = infer_kappa(g, q, lp)
        if kappa is not None and k == 0:
            covariant = True
            continue
        return None
    for st in reached:
        if peval(q, st) != k:
            return None
    return {"poly": q, "const": k,
            "kind": "conserved" if not covariant else "covariant-zero"}


def is_nontrivial(lp, q):
    """A claim counts as a real invariant if it relates >=2 variables or has
    degree >= 2 (single fixed variables are useless as assertions)."""
    touched = set()
    for m, c in q.items():
        if c == 0:
            continue
        for i, e in enumerate(m + (0,) * max(0, lp.n - len(m))):
            if e:
                touched.add(i)
    return len(touched) >= 2 or degree(q) >= 2


# ----------------------------------------------------------- driver

def run_symmetry(lp, mode="strict"):
    """Returns dict with validated claims for the requested candidate pool.
    mode='strict'  -> finite automorphism eigenforms only
    mode='extended'-> finite + translation duality
    """
    reached = simulate(lp)
    syms = detect_symmetries(lp)
    capped = len(syms) > MAX_IMAGES_FOR_EIGEN
    if capped:
        syms = syms[:MAX_IMAGES_FOR_EIGEN]

    finite = []
    seen = set()
    for image in syms:
        forms = eigen_candidates(lp, image)
        by_lam = {}
        for lam, poly in forms:
            by_lam.setdefault(lam, []).append(poly)
        combined = list(forms)
        for lam, polys in by_lam.items():
            for i in range(len(polys)):
                for j in range(i + 1, len(polys)):
                    combined.append((lam, padd(polys[i], polys[j])))
                    combined.append((lam, psub(polys[i], polys[j])))
        for lam, poly in combined:
            if not poly:
                continue
            key = normalize_vec(tuple(poly.get(m, Fraction(0))
                                      for m in monomial_basis(lp.n)))
            if key is None or key in seen:
                continue
            seen.add(key)
            finite.append(poly)

    trans = translation_candidates(lp) if mode == "extended" else []

    def dedup(polys):
        out, seenn = [], set()
        for p in polys:
            key = normalize_vec(tuple(p.get(m, Fraction(0))
                                      for m in monomial_basis(lp.n)))
            if key is None or key in seenn:
                continue
            seenn.add(key)
            out.append(p)
        return out

    claims = []
    for q in dedup(finite + trans):
        claim = validate_candidate(lp, q, reached)
        if claim and is_nontrivial(lp, claim["poly"]):
            # claims must constrain at least one mutated variable
            touched = set()
            for m, c in claim["poly"].items():
                for i, e in enumerate(m + (0,) * max(0, lp.n - len(m))):
                    if e:
                        touched.add(i)
            if touched & lp.mutated:
                claims.append(claim)
    return {"claims": claims, "n_syms": len(syms), "n_reached": len(reached),
            "syms_capped": capped}
