"""Exact rational polynomial engine + loop representation for stage 2.

Ported verbatim (poly operations) from experiments/noether-loop-invariants/
loops.py (stage 1). The hand-written benchmark (build_loops) is replaced by
CLoop, a loop representation extracted from real SV-COMP C sources by
parse_c.py.

Polys are dicts {exponent-tuple: Fraction}, trimmed of zero coefficients.
"""

from dataclasses import dataclass, field
from fractions import Fraction

Poly = dict


# ---------------------------------------------------------------- poly ops

def trim(p):
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


def lin(n, coefs, const=0):
    """Linear poly: coefs dict var->int, plus integer constant."""
    p = {tuple(1 if i == v else 0 for i in range(n)): Fraction(c)
         for v, c in coefs.items()}
    if const:
        p[()] = Fraction(const)
    return trim(p)


def mono(n, exps):
    return {tuple(exps): Fraction(1)}


# ------------------------------------------------------- loop spec (C-extracted)

@dataclass
class CLoop:
    """An integer while-loop extracted from C by parse_c.py.

    vars      : names of state variables (declared int-family scalars that
                the loop reads or writes)
    init      : concrete initial values (unknown ones fixed to 0 and listed
                in `params`)
    params    : indices of variables whose true initial value is unknown
                (nondet input or derived from one); used only for the
                numeric sanity pass
    guard_dnf : disjunction of conjunctions of (op, Poly) atoms -- the loop
                condition; used ONLY for the numeric sanity simulation
    branches  : ordered list of (conds, updates). conds: conjunction of
                (op, Poly) guarding this path (None = default), used only
                for simulation. updates: dict var index -> Poly next-state.
                Candidate validation uses updates only (sound: a conserved
                quantity is conserved on every branch regardless of guards).
    mutated   : set of variable indices assigned somewhere in the loop
    """

    name: str
    source: str                 # file path (+ line) for traceability
    vars: list
    init: list
    guard_dnf: list             # list[list[(op, Poly)]]
    branches: list              # list[(conds | None, dict)]
    mutated: set
    params: set = field(default_factory=set)

    @property
    def n(self):
        return len(self.vars)


OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def holds(op, val):
    return OPS[op](val, 0)


def guard_holds_term(term, state):
    return all(holds(op, peval(p, state)) for op, p in term)


def guard_holds(lp, state):
    """True iff state satisfies the loop guard (DNF). An empty DNF means a
    nondeterministic guard (`while (nondet())`) -- treated as true."""
    if not lp.guard_dnf:
        return True
    return any(guard_holds_term(t, state) for t in lp.guard_dnf)


def simulate(lp, cap=600):
    """States reachable from init while the guard holds (numeric sanity).
    Parametric variables are pinned to their recorded stand-in values."""
    state = list(lp.init)
    states = [tuple(state)]
    for _ in range(cap):
        if not guard_holds(lp, state):
            break
        fired = False
        for conds, upd in lp.branches:
            if conds is None or all(holds(op, peval(p, state))
                                    for op, p in conds):
                state = [int(peval(upd.get(i, lin(lp.n, {i: 1})), state))
                         for i in range(lp.n)]
                fired = True
                break
        if not fired:
            break
        if any(abs(v) > 2 ** 40 for v in state):
            break                       # overflow guard for scaling loops
        states.append(tuple(state))
    return states
