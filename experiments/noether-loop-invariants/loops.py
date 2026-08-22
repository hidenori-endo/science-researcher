"""Benchmark of ~30 small integer loops (SV-COMP style) with known
verification-grade invariants, plus a minimal exact polynomial engine
(pure stdlib) used to represent transition relations symbolically.

A loop is:
  vars      : names of integer program variables
  init      : initial values (aligned with vars)
  guard     : conjunction of (op, poly) predicates over the state; loop runs
              while all hold
  branches  : ordered list of (conds, updates). conds is a list of
              (op, poly) that must all hold for the branch to fire, or None
              for the default branch. updates maps var index -> poly giving
              the next-state value. Exactly one branch fires per step.

Polys are dicts {exponent-tuple: Fraction}, trimmed of zero coefficients.
"""

from dataclasses import dataclass
from fractions import Fraction

Poly = dict


# ---------------------------------------------------------------- poly ops

def trim(p):
    """Drop zero coefficients and pad all monomial keys to a common length
    (monomials must be full-length tuples for exponent addition to work)."""
    p = {m: c for m, c in p.items() if c != 0}
    if not p:
        return {}
    L = max(len(m) for m in p)
    return {m + (0,) * (L - len(m)): c for m, c in p.items()}


def padd(p, q):
    r = dict(p)
    for m, c in q.items():
        r[m] = r.get(m, Fraction(0)) + c
    return trim(r)


def pneg(p):
    return {m: -c for m, c in p.items()}


def psub(p, q):
    return padd(p, pneg(q))


def pscale(p, s):
    s = Fraction(s)
    return trim({m: c * s for m, c in p.items()})


def pmul(p, q):
    r = {}
    for m1, c1 in p.items():
        for m2, c2 in q.items():
            L = max(len(m1), len(m2))
            m1p = m1 + (0,) * (L - len(m1))
            m2p = m2 + (0,) * (L - len(m2))
            m = tuple(a + b for a, b in zip(m1p, m2p))
            r[m] = r.get(m, Fraction(0)) + c1 * c2
    return trim(r)


def ppow(p, k):
    r = {(): Fraction(1)}
    for _ in range(k):
        r = pmul(r, p)
    return r


def pconst(c):
    return {(): Fraction(c)} if Fraction(c) != 0 else {}


def peval(p, env):
    total = Fraction(0)
    for m, c in p.items():
        m = m + (0,) * max(0, len(env) - len(m))
        term = c
        for i, e in enumerate(m):
            if e:
                term *= Fraction(env[i]) ** e
        total += term
    return total


def degree(p):
    return max((sum(m) for m in p), default=0)


def pident(p, q):
    return trim(p) == trim(q)


def substitute(p, sub):
    """sub: dict var index -> poly. Returns p o sub."""
    r = {}
    for m, c in p.items():
        term = {(): Fraction(c)}
        for i, e in enumerate(m):
            if e:
                term = pmul(term, ppow(sub[i], e))
        r = padd(r, term)
    return r


def pstr(p, names):
    if not p:
        return "0"

    def keyfn(item):
        m, _ = item
        return (sum(m), m)

    parts = []
    for m, c in sorted(p.items(), key=keyfn):
        factors = []
        for i, e in enumerate(m):
            if e == 1:
                factors.append(names[i])
            elif e > 1:
                factors.append(f"{names[i]}^{e}")
        body = "*".join(factors)
        if not body:
            parts.append(("+ " if parts and c >= 0 else "- " if parts else "")
                         + f"{abs(c)}")
        else:
            coef = "" if abs(c) == 1 else f"{abs(c)}*"
            sign = "-" if c < 0 else ("+ " if parts else "")
            parts.append(("- " if sign == "-" else "+ " if parts else "")
                         + f"{coef}{body}")
    return " ".join(parts)


# ------------------------------------------------------- poly constructors

def lin(n, coefs, const=0):
    """Linear poly: coefs dict var->int, plus integer constant."""
    p = {tuple(1 if i == v else 0 for i in range(n)): Fraction(c)
         for v, c in coefs.items()}
    if const:
        p[()] = Fraction(const)
    return trim(p)


def mono(n, exps):
    return {tuple(exps): Fraction(1)}


# ------------------------------------------------------------- loop spec

@dataclass
class Loop:
    name: str
    desc: str
    vars: list
    init: list
    guard: list                      # list[(op, Poly)]
    guard_str: str
    branches: list                   # list[(conds|None, dict var->Poly)]
    invariant_strs: list             # human-readable known invariants
    target: Poly                     # target post-condition: target == target_const
    target_const: Fraction
    notes: str = ""

    @property
    def n(self):
        return len(self.vars)


def cond(op, p):
    return (op, p)


def GB(op, i, bound, nref):
    """guard atom: x_i <op> bound, encoded as (op, x_i - bound)."""
    return (op, lin(nref, {i: 1}, const=-bound))


# --------------------------------------------------------- the benchmark

def build_loops():
    L = []

    def mk(name, desc, vars_, init, guard_str, guard, branches,
           invariant_strs, target_poly, target_const, notes=""):
        L.append(Loop(name, desc, vars_, list(init), guard, guard_str,
                      branches, invariant_strs,
                      target_poly, Fraction(target_const)
                      if target_const is not None else None, notes))

    def V(i, c=1, k=0):
        """poly  c*x_i + k  (an affine update / guard atom)."""
        return lin(len_["n"], {i: c}, const=k)

    def Sum(*ps):
        out = {}
        for p in ps:
            out = padd(out, p)
        return out

    len_ = {}

    # 1. two counters incremented together; swap symmetry -> x - y
    n = len_["n"] = 2
    mk("pair-inc", "two counters incremented in lockstep",
       ["x", "y"], [0, 0], "x < 10", [GB("<", 0, 10, n)],
       [(None, {0: V(0, 1, 1), 1: V(1, 1, 1)})],
       ["x - y == 0"], lin(n, {0: 1, 1: -1}), 0)

    # 2. counters with constant steps 2 and 1
    mk("ratio-step", "counters with constant steps 2 and 1",
       ["x", "y"], [0, 0], "x < 20", [GB("<", 0, 20, n)],
       [(None, {0: V(0, 1, 2), 1: V(1, 1, 1)})],
       ["x - 2*y == 0"], lin(n, {0: 1, 1: -2}), 0)

    # 3. both variables double each iteration; scaling symmetry
    mk("doubling-eq", "both variables double each iteration",
       ["x", "y"], [1, 1], "x < 100", [GB("<", 0, 100, n)],
       [(None, {0: V(0, 2), 1: V(1, 2)})],
       ["x - y == 0"], lin(n, {0: 1, 1: -1}), 0)

    # 4. lo++ / hi-- pointers meeting in the middle
    mk("meet-middle", "lo++ / hi-- pointers meeting in the middle",
       ["lo", "hi"], [0, 16], "lo < hi", [cond("<", lin(n, {0: 1, 1: -1}))],
       [(None, {0: V(0, 1, 1), 1: V(1, 1, -1)})],
       ["lo + hi == 16"], lin(n, {0: 1, 1: 1}), 16)

    # 5. mass moves from x to y one unit at a time
    mk("converge", "mass moves from x to y one unit at a time",
       ["x", "y"], [10, 0], "x > y", [cond(">", lin(n, {0: 1, 1: -1}))],
       [(None, {0: V(0, 1, -1), 1: V(1, 1, 1)})],
       ["x + y == 10"], lin(n, {0: 1, 1: 1}), 10)

    # 6. skewed transfer x -= 2 while y += 1
    mk("skew-decrement", "skewed transfer x-=2, y+=1",
       ["x", "y"], [20, 0], "x > 0", [cond(">", V(0))],
       [(None, {0: V(0, 1, -2), 1: V(1, 1, 1)})],
       ["x + 2*y == 20"], lin(n, {0: 1, 1: 2}), 20)

    # 7. three counters with steps 2, 3, 5
    n = len_["n"] = 3
    mk("weighted-triple", "three counters with constant steps 2, 3, 5",
       ["x", "y", "z"], [0, 0, 0], "x < 30", [GB("<", 0, 30, n)],
       [(None, {0: V(0, 1, 2), 1: V(1, 1, 3), 2: V(2, 1, 5)})],
       ["5*y - 3*z == 0"], lin(n, {1: 5, 2: -3}), 0)

    # 8. x drains by 1 while y and z each grow by 1
    mk("drain-two-sinks", "x drains by 1 while y and z each grow by 1",
       ["x", "y", "z"], [12, 0, 0], "x > 0", [cond(">", V(0))],
       [(None, {0: V(0, 1, -1), 1: V(1, 1, 1), 2: V(2, 1, 1)})],
       ["x + y == 12", "y - z == 0"], lin(n, {1: 1, 2: -1}), 0)

    # 9. rectangle w/h trade-off at fixed half-perimeter
    n = len_["n"] = 2
    mk("area-perimeter", "rectangle w/h trade-off at fixed half-perimeter",
       ["w", "h"], [3, 9], "w < h", [cond("<", lin(n, {0: 1, 1: -1}))],
       [(None, {0: V(0, 1, 1), 1: V(1, 1, -1)})],
       ["w + h == 12"], lin(n, {0: 1, 1: 1}), 12)

    # 10. s accumulates 0+1+...+(i-1); quadratic conserved quantity
    n = len_["n"] = 2
    mk("gauss-sum", "s += i before i++; sum of first integers",
       ["i", "s"], [0, 0], "i <= 10", [GB("<=", 0, 10, n)],
       [(None, {0: V(0, 1, 1), 1: Sum(V(1), V(0))})],
       ["2*s - i^2 + i == 0"],
       psub(lin(n, {1: 2}), padd(mono(n, (2, 0)), pneg(lin(n, {0: 1})))), 0,
       notes="quadratic conserved quantity; no finite point symmetry")

    # 11. even prefix sums
    mk("sum-even", "s += i with i += 2 (even prefix sums)",
       ["i", "s"], [0, 0], "i < 12", [GB("<", 0, 12, n)],
       [(None, {0: V(0, 1, 2), 1: Sum(V(1), V(0))})],
       ["4*s - i^2 + 2*i == 0"],
       psub(lin(n, {1: 4}), padd(mono(n, (2, 0)), lin(n, {0: -2}))), 0,
       notes="quadratic conserved quantity")

    # 12. running factorial-like product
    mk("product-count", "p *= n while n++ (factorial)",
       ["n", "p"], [1, 1], "n < 5", [GB("<", 0, 5, n)],
       [(None, {0: V(0, 1, 1),
                1: pmul(lin(n, {0: 1}), lin(n, {1: 1}))})],
       ["p == n! (non-polynomial)"], None, None,
       notes="target not expressible as polynomial equality")

    # 13. subtractive Euclid
    mk("gcd-subtract", "subtractive Euclid gcd",
       ["a", "b"], [48, 18], "a != b",
       [cond("!=", lin(n, {0: 1, 1: -1}))],
       [([cond(">", lin(n, {0: 1, 1: -1}))],
         {0: psub(V(0), V(1)), 1: V(1)}),
        (None, {0: V(0), 1: psub(V(1), V(0))})],
       ["gcd(a,b) == 6 (non-polynomial)"], None, None,
       notes="invariant is a non-arithmetic function (gcd)")

    # 14. Fibonacci recurrence pair
    mk("fib-pair", "(a,b) <- (b,a+b): Fibonacci pair",
       ["a", "b"], [0, 1], "b < 50", [GB("<", 1, 50, n)],
       [(None, {0: V(1), 1: Sum(V(0), V(1))})],
       ["b == Fib(t) (non-polynomial)"], None, None,
       notes="only an irrational-scaling approximate symmetry (golden ratio)")

    # 15. three equal counters decrement in lockstep
    n = len_["n"] = 3
    mk("symmetric-dec3", "three equal counters decrement in lockstep",
       ["x", "y", "z"], [30, 30, 30], "x > 0", [cond(">", V(0))],
       [(None, {0: V(0, 1, -1), 1: V(1, 1, -1), 2: V(2, 1, -1)})],
       ["x - z == 0"], lin(n, {0: 1, 2: -1}), 0)

    # 16. counters with constant steps 4 and 6
    n = len_["n"] = 2
    mk("cross-scale-step", "counters with constant steps 4 and 6",
       ["x", "y"], [0, 0], "x < 40", [GB("<", 0, 40, n)],
       [(None, {0: V(0, 1, 4), 1: V(1, 1, 6)})],
       ["3*x - 2*y == 0"], lin(n, {0: 3, 1: -2}), 0)

    # 17. i++, s += 2, t += 3
    n = len_["n"] = 3
    mk("affine-counters", "i++, s += 2, t += 3",
       ["i", "s", "t"], [0, 0, 0], "i < 10", [GB("<", 0, 10, n)],
       [(None, {0: V(0, 1, 1), 1: V(1, 1, 2), 2: V(2, 1, 3)})],
       ["t - 3*i == 0"], lin(n, {0: -3, 2: 1}), 0)

    # 18. counters with constant steps 1, 2, 3
    mk("ladder-123", "counters with constant steps 1, 2, 3",
       ["x", "y", "z"], [0, 0, 0], "x < 15", [GB("<", 0, 15, n)],
       [(None, {0: V(0, 1, 1), 1: V(1, 1, 2), 2: V(2, 1, 3)})],
       ["3*x - z == 0"], lin(n, {0: 3, 2: -1}), 0)

    # 19. two counters decrement together from unequal starts
    n = len_["n"] = 2
    mk("parallel-dec", "two counters decrement together from 50 and 20",
       ["x", "y"], [50, 20], "x > 0", [cond(">", V(0))],
       [(None, {0: V(0, 1, -1), 1: V(1, 1, -1)})],
       ["x - y == 30"], lin(n, {0: 1, 1: -1}), 30)

    # 20. both variables multiply by -2 (sign-flip + scaling symmetry)
    mk("neg-scale-pair", "both variables multiply by -2",
       ["x", "y"], [1, 3], "x < 100", [GB("<", 0, 100, n)],
       [(None, {0: V(0, -2), 1: V(1, -2)})],
       ["3*x - y == 0"], lin(n, {0: 3, 1: -1}), 0)

    # 21. x doubles while y quadruples: y tracks x^2
    mk("square-track", "x*=2, y*=4 so y tracks x squared",
       ["x", "y"], [1, 1], "x < 50", [GB("<", 0, 50, n)],
       [(None, {0: V(0, 2), 1: V(1, 4)})],
       ["y - x^2 == 0"],
       psub(lin(n, {1: 1}), mono(n, (2, 0))), 0,
       notes="nonlinear invariant from mixed-rate scaling symmetry")

    # 22. same with rates 3 and 9
    mk("square-track3", "x*=3, y*=9 so y tracks x squared",
       ["x", "y"], [1, 1], "x < 60", [GB("<", 0, 60, n)],
       [(None, {0: V(0, 3), 1: V(1, 9)})],
       ["y - x^2 == 0"],
       psub(lin(n, {1: 1}), mono(n, (2, 0))), 0)

    # 23. y tracks x cubed but our candidate bound is degree 2
    mk("cube-miss", "x*=2, y*=8 so y tracks x cubed",
       ["x", "y"], [1, 1], "x < 40", [GB("<", 0, 40, n)],
       [(None, {0: V(0, 2), 1: V(1, 8)})],
       ["y - x^3 == 0"],
       psub(lin(n, {1: 1}), mono(n, (3, 0))), 0,
       notes="invariant has degree 3 > search bound 2")

    # 24. permutation-symmetric lockstep decrement
    n = len_["n"] = 3
    mk("perm3", "three equal counters decrement in lockstep (perm variant)",
       ["x", "y", "z"], [5, 5, 5], "x > 0", [cond(">", V(0))],
       [(None, {0: V(0, 1, -1), 1: V(1, 1, -1), 2: V(2, 1, -1)})],
       ["y - z == 0"], lin(n, {1: 1, 2: -1}), 0)

    # 25. conditionally-routed increments keep a deficit zero
    mk("cond-split", "first 5 steps fill y, then fill z; x-y-z stays 0",
       ["x", "y", "z"], [0, 0, 0], "x < 10", [GB("<", 0, 10, n)],
       [([cond("<", V(0, 1, -5))],
         {0: V(0, 1, 1), 1: V(1, 1, 1), 2: V(2)}),
        (None,
         {0: V(0, 1, 1), 1: V(1), 2: V(2, 1, 1)})],
       ["x - y - z == 0"], lin(n, {0: 1, 1: -1, 2: -1}), 0)

    # 26. both variables multiply by 3; scaling symmetry
    n = len_["n"] = 2
    mk("triple-scale", "both variables multiply by 3",
       ["x", "y"], [2, 4], "x < 200", [GB("<", 0, 200, n)],
       [(None, {0: V(0, 3), 1: V(1, 3)})],
       ["2*x - y == 0"], lin(n, {0: 2, 1: -1}), 0)

    # 27. rotating triple with a step counter; cyclic perm automorphism
    n = len_["n"] = 4
    mk("rotate-counter", "(x,y,z) rotates right each step, n counts steps",
       ["n", "x", "y", "z"], [0, 1, 2, 3], "n < 6", [GB("<", 0, 6, n)],
       [(None, {0: V(0, 1, 1), 1: V(2), 2: V(3), 3: V(1)})],
       ["x + y + z == 6"], lin(4, {1: 1, 2: 1, 3: 1}), 6,
       notes="cyclic variable permutation is a transition automorphism")

    # 28. asymmetric convergence x += 3, y -= 1 from (0, 24)
    n = len_["n"] = 2
    mk("mirror-sum", "asymmetric convergence x+=3, y-=1 from (0,24)",
       ["x", "y"], [0, 24], "x < 24", [GB("<", 0, 24, n)],
       [(None, {0: V(0, 1, 3), 1: V(1, 1, -1)})],
       ["x + 3*y == 72"], lin(n, {0: 1, 1: 3}), 72)

    # 29. lockstep counters from unequal starts
    mk("offset-parity", "lockstep counters starting at 3 and -6",
       ["x", "y"], [3, -6], "x < 500", [GB("<", 0, 500, n)],
       [(None, {0: V(0, 1, 1), 1: V(1, 1, 1)})],
       ["x - y == 9"], lin(n, {0: 1, 1: -1}), 9)

    # 30. flattened nested loop needs a phase bit
    n = len_["n"] = 3
    zero = {}
    one = lin(n, {}, const=1)
    mk("nested-flatten",
       "flattened nested loop: outer i++, inner j over i, phase bit p",
       ["i", "j", "p"], [0, 0, 0], "i < 3", [GB("<", 0, 3, n)],
       [([cond("==", V(2))],
         {0: V(0, 1, 1), 1: zero, 2: one}),
        ([cond("==", V(2)),
          cond("<", lin(n, {1: 1, 0: -1}, const=-1))],
         {0: V(0), 1: V(1, 1, 1), 2: one}),
        (None,
         {0: V(0), 1: V(1, 1, 1), 2: zero})],
       ["0 <= j <= i <= 3 (inequalities; outside equality fragment)"],
       None, None,
       notes="control-heavy: verification-grade invariant is disjunctive/inequality")

    return L


if __name__ == "__main__":
    for lp in build_loops():
        print(f"{lp.name:20s} vars={lp.vars} init={lp.init} "
              f"inv={lp.invariant_strs}")
