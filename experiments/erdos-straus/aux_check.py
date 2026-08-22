#!/usr/bin/env python3
"""
AUXILIARY boundary-check script for experiments/erdos-straus/THEORY.md.

NOT the deliverable. Confirms boundary cases of hand-proved lemmas and
pre-registered falsification tests for the new conjecture H* stated in
THEORY.md. Small ranges only; no search-bound-extension claims.

Structural dichotomy (Lemma 4 in THEORY.md, proved by hand):
  For prime p, every solution 4/p = 1/x+1/y+1/z has a p-divisible
  variable v = p*z' such that
    (D)  p | 4z'-1                      [degenerate family], or
    (G)  exists s | z'*z' with 4z'-1 | s + p*z'   [generic family].

Conjecture H* (pre-registered, see THEORY.md section 4):
  A prime p admits a family-G solution  iff  p mod 840 is NOT one of the
  six exceptional residues {1, 121, 169, 289, 361, 529}.
Cheap falsification thresholds used here (fixed BEFORE running):
  - exceptional primes p <= 10000: G-search over 1 <= z' <= 100000;
    any hit falsifies H*.
  - non-exceptional primes p <= 400: G-search over z' <= 20000;
    any miss falsifies H*.
"""

import sys
from math import gcd, isqrt

EXCEPTIONAL = {1, 121, 169, 289, 361, 529}


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    r = isqrt(n)
    for f in range(3, r + 1, 2):
        if n % f == 0:
            return False
    return True


def spf_sieve(n):
    """smallest prime factor table up to n."""
    spf = list(range(n + 1))
    for i in range(2, isqrt(n) + 1):
        if spf[i] == i:
            for j in range(i * i, n + 1, i):
                if spf[j] == j:
                    spf[j] = i
    return spf


SPF = spf_sieve(200001)


def factor(n):
    fac = {}
    while n > 1:
        f = SPF[n]
        cnt = 0
        while n % f == 0:
            n //= f
            cnt += 1
        fac[f] = cnt
    return fac


def divisors_sq(fac, cap=20000):
    """divisors of z'^2 given factorization dict of z'; None if too many."""
    total = 1
    for e in fac.values():
        total *= 2 * e + 1
    if total > cap:
        return None
    ds = [1]
    for f, e in fac.items():
        pk = 1
        new = []
        for _ in range(2 * e + 1):
            for d in ds:
                new.append(d * pk)
            pk *= f
        ds = new
    return ds


def has_G_solution(p, zmax, want_first=False):
    """Search z' <= zmax for (G): exists s | z'^2 with 4z'-1 | s + p z'.
       Returns (found_bool, smallest_z_or_None)."""
    for z in range(1, zmax + 1):
        m = 4 * z - 1
        target = (-p * z) % m
        ds = divisors_sq(factor(z))
        if ds and any(s % m == target for s in ds):
            return True, (z if want_first else None)
    return False, None


def all_solutions_prime(p):
    """All solutions 4/p = 1/x+1/y+1/z, x<=y<=z, via SFFT on x."""
    sols = []
    N = p * p
    for x in range(p // 4 + 1, (3 * p) // 4 + 1):
        q = 4 * x - p
        M = N * x * x
        target = (-p * x) % q
        i = 1
        while i * i <= M:
            if M % i == 0:
                for a in {i, M // i}:
                    b = M // a
                    if a <= b and a % q == target and b % q == target:
                        y = (a + p * x) // q
                        z = (b + p * x) // q
                        if y >= x and z >= y:
                            sols.append((x, y, z))
            i += 1
    return sorted(set(sols))


def classify_solution(p, sol):
    """Check dichotomy: some p-divisible variable satisfies (D) or (G)."""
    for v in sol:
        if v % p:
            continue
        zp = v // p
        m = 4 * zp - 1
        if m % p == 0:
            return True, "D"
        # (G): exists s | zp^2 with m | s + p*zp
        target = (-p * zp) % m
        ds = divisors_sq(factor(zp), cap=10**7)
        if ds and any(s % m == target for s in ds):
            return True, "G"
    return False, None


def main():
    print("=== CHECK 1: dichotomy (D)/(G) on ALL solutions for primes <= 48 ===")
    bad = tot = 0
    famcount = {"D": 0, "G": 0}
    for p in range(3, 49):
        if not is_prime(p):
            continue
        for sol in all_solutions_prime(p):
            ok, fam = classify_solution(p, sol)
            tot += 1
            if ok:
                famcount[fam] += 1
            else:
                bad += 1
                print(f"  !! dichotomy FAILS p={p} sol={sol}")
    print(f"  {tot} solutions checked, failures={bad}, family counts={famcount}")

    print("\n=== CHECK 2: small-modulus family-G classes (m | 840) ===")
    # classes c mod m from (z', s): m = 4z'-1 | 840, c = -s*z'^-1 mod m
    cov3, cov7, cov15, cov35 = set(), set(), set(), set()
    for z in range(1, 300):
        m = 4 * z - 1
        if 840 % m != 0:
            continue
        ds = divisors_sq(factor(z))
        zs_inv = pow(z, -1, m)
        cls = {(-s * zs_inv) % m for s in ds}
        print(f"  m={m:3d} (z'={z:3d}): classes mod {m}: {sorted(cls)}")
        if m == 3:
            cov3 = cls
        elif m == 7:
            cov7 = cls
        elif m == 15:
            cov15 = cls
        elif m == 35:
            cov35 = cls
    survivors = []
    for r in range(1, 840, 2):
        if gcd(r, 840) != 1:
            continue
        if r % 3 in cov3 or r % 7 in cov7 or r % 15 in cov15 or r % 35 in cov35:
            continue
        survivors.append(r)
    print(f"  units mod 840 not covered by ANY small (m|840) G-class "
          f"({len(survivors)} of 192):")
    print(f"  {survivors}")
    print(f"  superset of EXCEPTIONAL? "
          f"{set(EXCEPTIONAL) <= set(survivors)}")

    print("\n=== CHECK 3 [pre-registered falsification of H*, forward dir] ===")
    print("  exceptional primes p<=10000, G-search z'<=100000 "
          "(any hit falsifies H*)")
    exc_primes = [p for p in range(3, 10001)
                  if is_prime(p) and p % 840 in EXCEPTIONAL]
    print(f"  exceptional primes found: {exc_primes}")
    for p in exc_primes:
        ok, _ = has_G_solution(p, 100000)
        print(f"    p={p:5d}: G-solution in z'<=100000? {ok}"
              + ("   <-- FALSIFIES H*" if ok else ""))

    print("\n=== CHECK 4 [pre-registered falsification of H*, reverse dir] ===")
    print("  non-exceptional primes p<=400, G-search z'<=20000 "
          "(any miss falsifies H*)")
    miss = []
    np_ = 0
    for p in range(3, 401):
        if not is_prime(p) or p % 840 in EXCEPTIONAL:
            continue
        np_ += 1
        ok, _ = has_G_solution(p, 20000)
        if not ok:
            miss.append(p)
    print(f"  {np_} primes tested, misses: {miss if miss else 'none'}")

    print("\n=== CHECK 5: family-D certificates for exceptional primes ===")
    def find_cert(p, gmax):
        out = []
        for g in range(1, gmax + 1):
            C = p * (p + 4 * g)
            for d in divisors(C):
                if (d + p) % (4 * g) == 0:
                    L = (d + p) // (4 * g)
                    if d == 4 * g * L - p and (p * L + 1) % d == 0:
                        K = (p * L + 1) // d
                        x, y, zz = g * K, g * L, p * g * K * L
                        assert 4 * x * y * zz == p * (x*y + x*zz + y*zz)
                        assert 4*g*K*L == p*(K+L) + 1  # identity check
                        out.append((g, L, K))
                        break
        return out
    def divisors(n):
        ds = []
        i = 1
        while i * i <= n:
            if n % i == 0:
                ds.append(i)
                if i != n // i:
                    ds.append(n // i)
            i += 1
        return ds
    for p in exc_primes[:8]:
        certs = find_cert(p, 600)
        if certs:
            g, L, K = min(certs, key=lambda c: c[1])
            print(f"    p={p:5d}: min-L cert g={g:4d} L={L:6d} K={K:6d} "
                  f" max-param/p = {max(g,L,K)/p:.2f}")
        else:
            print(f"    p={p:5d}: no cert with g<=600")

    print("\n=== CHECK 6: F1 is a PROPER subfamily of family (G) ===")
    print("  (added 2026-08-23 with the re-verdict; supports THEORY.md 5.1)")
    print("  F1 restricts sigma to sigma = z'*w with w | z'. Listing primes")
    print("  that admit a family-G witness whose sigma is NOT of that form.")
    witnesses = []
    for p in range(5, 200):
        if not is_prime(p):
            continue
        hit = None
        for z in range(1, 400):
            m = 4 * z - 1
            if p % m == 0:          # family (D), not (G)
                continue
            ds = divisors_sq(factor(z), cap=10**6)
            if not ds:
                continue
            f1_sigmas = {z * w for w in divisors(z)}
            target = (-p * z) % m
            for s in ds:
                if s % m == target and s not in f1_sigmas:
                    hit = (p, z, m, s)
                    break
            if hit:
                break
        if hit:
            witnesses.append(hit)
    print(f"  primes p<200 with a non-F1 family-G witness: {len(witnesses)}")
    print(f"  first eight (p, z', m=4z'-1, sigma): {witnesses[:8]}")
    print("  note: sigma=1 with z'>1 is never of the form z'*w, so the")
    print("  sigma=1 route of THEORY.md 2.5 lies outside F1 entirely.")

    print("\n=== CHECK 7: THEORY (D)/(G) vs the Bradford divisor condition ===")
    print("  (added 2026-08-23; supports THEORY.md 8.2)")
    print("  Bradford: exists x with ceil(p/4)<=x<=ceil(p/2) and d | x*x with")
    print("    d = -p*x (mod 4x-p),  or  d <= x and d = -x (mod 4x-p).")
    print("  THEORY:   exists z' with (D) p | 4z'-1, or")
    print("            (G) exists sigma | z'^2 with 4z'-1 | sigma + p*z'.")
    print("  Both are the SFFT divisor condition of the same equation; they")
    print("  differ only in which denominator is eliminated first.")

    def bradford(p):
        lo = -(-p // 4)
        hi = -(-p // 2)
        for x in range(lo, hi + 1):
            q = 4 * x - p
            if q <= 0:
                continue
            ds = divisors(x * x)
            if any(d % q == (-p * x) % q for d in ds):
                return x, "I"
            if any(d <= x and d % q == (-x) % q for d in ds):
                return x, "II"
        return None

    def theory(p):
        for z in range(1, 300):
            m = 4 * z - 1
            if m % p == 0:
                return z, "D"
            ds = divisors_sq(factor(z), cap=10**6)
            if ds and any(s % m == (-p * z) % m for s in ds):
                return z, "G"
        return None

    mismatch = 0
    tested = 0
    for p in range(3, 200):
        if not is_prime(p):
            continue
        tested += 1
        b, t = bradford(p), theory(p)
        if (b is None) != (t is None):
            mismatch += 1
            print(f"  !! p={p}: bradford={b} theory={t}")
    print(f"  {tested} primes tested, solvability disagreements: {mismatch}")
    print("  (agreement is expected and is NOT evidence of novelty: both")
    print("   conditions are equivalent to E-S for p, so this only confirms")
    print("   the two normalizations are the same construction.)")


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    main()
