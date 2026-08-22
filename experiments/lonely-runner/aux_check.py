"""Auxiliary boundary checks for experiments/lonely-runner/THEORY.md.

NOT a search-bound extension. Every computation confirms a boundary case or
numeric value of a lemma stated in THEORY.md:

  C1. Exact delta(S) for extremal/reference speed sets. Objective
      g(t)=min_i ||a_i t|| is piecewise linear; its maximum is attained at a
      vertex of the arrangement: a kink of some f_i (t=m/(2a_i)) or a
      crossing of two f_i (t=m/(a_i-a_j) or m/(a_i+a_j)).
  C2. Exact resonance identity (EQ* in Section 4):
          mu(cap_{i in S} B_i) = sum_m prod_{i in S} shat(m*L/a_i),
      shat(0)=2eps, shat(x)=sin(2 pi x eps)/(pi x), L=lcm(a_i : i in S).
      Verified against exact tooth-overlap arithmetic.
  C3. Pairwise defect Delta_2 = mu(B_a cap B_b)-(2eps)^2 versus reduced
      entry size (input to the Bonferroni budget of Section 5).
  C4. Triple-intersection defects versus (2eps)^3 (status of Lemma D).
  C5. Uncovered measure mu(U) for 8-speed sets versus the random model
      (7/9)^8 -- quantifies the slack available at k=8.

eps = 1/(k+1); B_a = {t : ||a t|| < eps}; U = [0,1) \ union B_i;
delta(a) = max_t min_i ||t a_i||.
"""
import math
import random
from fractions import Fraction as F

random.seed(1907)
EPS = F(1, 9)
EPSe = float(EPS)


def dist(x):
    return min(x - math.floor(x), math.ceil(x) - x)


# ---------- C1 ----------

def delta_exact(speeds):
    cand = set()
    for a in speeds:
        for m in range(2 * a):
            cand.add(m / (2 * a))
    for i in range(len(speeds)):
        for j in range(i + 1, len(speeds)):
            for den in (speeds[i] - speeds[j], speeds[i] + speeds[j]):
                if den > 0:
                    for m in range(den):
                        cand.add(m / den)
    best, bt = -1.0, None
    for t in cand:
        v = min(dist(t * a) for a in speeds)
        if v > best:
            best, bt = v, t
    return best, bt


def frac_str(t):
    p = round(t * 10**9)
    g = math.gcd(p, 10**9)
    return f"{p//g}/{10**9//g}"


print("=== C1: exact delta for extremal / reference sets ===")
for S in [(1, 2), (2, 3), (5, 7), (1, 2, 3), (1, 2, 4), (1, 3, 4),
          tuple(range(1, 9))]:
    d, t = delta_exact(S)
    print(f"S={list(S)}  k={len(S)}  1/(k+1)={1/len(S)/(1+1/len(S)):.6f}"
          f"  delta={d:.9f}  argmax~{frac_str(t)}")

# ---------- helpers for C2/C3 ----------

def circ_dist(c1, c2):
    d = abs(c1 - c2) % 1
    return min(d, 1 - d)


def mu_intersect_pair(a, b, eps):
    """Exact mu(B_a cap B_b) by summing circular overlaps of teeth.
    Valid because each tooth is a circular arc of width 2eps/a <= 2/9 < 1/2
    and two such arcs overlap in a single arc (containment handled)."""
    ra, rb = F(eps) / a, F(eps) / b
    tot = F(0)
    for ma in range(a):
        c1 = F(ma, a)
        for mb in range(b):
            d = circ_dist(c1, F(mb, b))
            if d <= abs(ra - rb):
                ov = 2 * min(ra, rb)
            else:
                ov = max(F(0), ra + rb - d)
            tot += ov
    return tot


def shat(k, eps):
    if k == 0:
        return 2 * eps
    return math.sin(2 * math.pi * k * eps) / (math.pi * k)


def mu_fourier(speeds, eps, M=100000):
    """EQ*: mu(cap B_{a_i}) = sum_m prod_i shat(m*L/a_i)."""
    L = 1
    for a in speeds:
        L = L * a // math.gcd(L, a)
    args = [L // a for a in speeds]
    return sum(math.prod(shat(m * x, eps) for x in args)
               for m in range(-M, M + 1))


print()
print("=== C2: resonance identity EQ* vs exact teeth arithmetic ===")
for pair in [(1, 2), (1, 3), (2, 6), (10, 11), (30, 31),
             (97, 211), (300, 301)]:
    ft = mu_fourier(pair, EPSe)
    tt = float(mu_intersect_pair(pair[0], pair[1], EPS))
    print(f"pair {pair}: EQ* = {ft:.9f}  teeth-exact = {tt:.9f}  "
          f"|diff| = {abs(ft - tt):.2e}")

print()
print("=== C3: pairwise defect Delta_2 vs reduced entry size ===")
base = (2 * EPSe) ** 2
print(f"(2 eps)^2 = {base:.9f}")
for pair in [(1, 2), (1, 3), (10, 11), (30, 31), (97, 98), (300, 301)]:
    mu = float(mu_intersect_pair(*pair, EPS))
    g = math.gcd(*pair)
    print(f"pair {pair} (reduced {pair[0]//g},{pair[1]//g}): "
          f"mu = {mu:.9f}  Delta_2 = {mu - base:+.3e}")

print()
print("=== C4: triple defects vs (2 eps)^3 (Monte Carlo, 5e6 samples) ===")
tri_base = (2 * EPSe) ** 3
print(f"(2 eps)^3 = {tri_base:.9f}")


def mu_inside_mc(speeds, eps, n=5_000_000):
    """MC estimate of mu(cap_i B_{a_i}): fraction of t inside EVERY tube."""
    hit = 0
    for _ in range(n):
        t = random.random()
        ok = True
        for a in speeds:
            u = t * a % 1
            if not (u < eps or u > 1 - eps):
                ok = False
                break
        if ok:
            hit += 1
    return hit / n


def mu_outside_mc(speeds, eps, n=5_000_000):
    """MC estimate of mu(U): fraction of t outside every tube."""
    hit = 0
    for _ in range(n):
        t = random.random()
        ok = True
        for a in speeds:
            u = t * a % 1
            if u < eps or u > 1 - eps:
                ok = False
                break
        if ok:
            hit += 1
    return hit / n


for tri in [(10, 11, 12), (50, 51, 52), (1000, 1001, 1002),
            (137, 251, 503)]:
    mu = mu_inside_mc(tri, EPSe)
    err = 3 * math.sqrt(max(mu * (1 - mu) / 5e6, 1e-12))
    print(f"triple {tri}: mu(cap B) ~ {mu:.6f} (+/-{err:.6f})  "
          f"Delta_3 ~ {mu - tri_base:+.3e}")

print()
print("=== C5: uncovered measure mu(U), k=8, eps=1/9 (MC 5e6) ===")
print(f"random model (7/9)^8 = {(7/9)**8:.9f}")
generic = (137, 251, 359, 503, 641, 769, 887, 997)
consec = tuple(range(50, 58))
for name, S in [("generic primes     ", generic),
                ("consecutive 50..57 ", consec)]:
    mu = mu_outside_mc(S, EPSe)
    err = 3 * math.sqrt(max(mu * (1 - mu) / 5e6, 1e-12))
    print(f"{name}: mu(U) ~ {mu:.6f} (+/-{err:.6f})")

print()
print("=== C5b: exact delta(50..57) (arrangement vertices) ===")
d, t = delta_exact(consec)
print(f"delta(50..57) = {d:.9f} >= 1/9   argmax ~ {frac_str(t)}")
