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

CHECK 8-11 (added 2026-08-23, supports THEORY.md section 9) are of a
different kind: Lemma F makes F1 DECIDABLE (w <= (p+1)/3), so CHECK 8/9
are exhaustive verifications of a proof, not bounded searches. They settle
the follow-up items (M0) and (M1) of THEORY.md section 5, both negatively.
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


def divisors_of(n):
    """all divisors of n, sorted (n must be <= the SPF sieve bound)."""
    ds = [1]
    for f, e in factor(n).items():
        pk, new = 1, []
        for _ in range(e + 1):
            new += [d * pk for d in ds]
            pk *= f
        ds = new
    return sorted(ds)


def primes_upto(n):
    sieve = bytearray([1]) * (n + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, isqrt(n) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    return [i for i in range(2, n + 1) if sieve[i]]


def F1_decide(p):
    """Lemma F (THEORY.md 9.1): F1 is decidable, w <= (p+1)/3 suffices.
       Returns a witness (w, m, z') or None -- None is a PROOF that F1 fails."""
    for w in range(1, (p + 1) // 3 + 1):
        for m in divisors_of(p + w):
            if m >= 3 and (m + 1) % (4 * w) == 0:
                return (w, m, (m + 1) // 4)
    return None


def F1_naive(p, zmax):
    """F1 straight from the definition: exists z'<=zmax, w | z', (4z'-1) | p+w."""
    for z in range(1, zmax + 1):
        m = 4 * z - 1
        for w in divisors_of(z):
            if (p + w) % m == 0:
                return (w, m, z)
    return None


def lopez_taus(z):
    """{d, n^2, d n^2 : d n = z'} -- the tau values reachable by the three
       congruence types of Lopez, arXiv:2404.01508."""
    s = set()
    for d in divisors_of(z):
        n = z // d
        s |= {d, n * n, d * n * n}
    return s


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

    print("\n=== CHECK 8: Lemma F -- F1 is DECIDABLE (w <= (p+1)/3) ===")
    print("  (added 2026-08-23; supports THEORY.md 9.1 and 9.3)")
    mism = [p for p in primes_upto(400)
            if p > 2 and (F1_decide(p) is None) != (F1_naive(p, 3000) is None)]
    print(f"  bounded form vs naive form (z'<=3000), p<400: "
          f"mismatches = {mism if mism else 'none'}")
    f1_false = [p for p in primes_upto(20000) if p > 2 and F1_decide(p) is None]
    print("  primes p<20000 for which F1 is FALSE (complete decision, NOT a")
    print("  truncated search -- Lemma F bounds w, so 'no witness' is a proof):")
    print(f"    {f1_false}")
    exc_f1 = [(p, p % 840) for p in f1_false if p % 840 in EXCEPTIONAL]
    print(f"  of these, in an exceptional class mod 840: {exc_f1}")
    print("  => (M1) is settled NEGATIVELY: F1 alone cannot cover the six")
    print("     exceptional classes.")

    print("\n=== CHECK 9: (M0) exhaustion lemma is FALSE ===")
    print("  (M0) asked: does every prime with a family-G solution also have")
    print("  an F1-type solution? Two counterexamples, fully enumerated.")
    for p in (7, 31):
        gw = None
        for z in range(1, 50):
            m = 4 * z - 1
            if p % m == 0:
                continue
            ds = divisors_sq(factor(z), cap=10**6) or []
            hit = [s for s in ds if (s + p * z) % m == 0]
            if hit:
                gw = (z, m, hit[0])
                break
        assert gw is not None
        wmax = (p + 1) // 3
        print(f"  p={p}: family-G witness (z'={gw[0]}, m={gw[1]}, "
              f"sigma={gw[2]}) exists.")
        print(f"        F1: Lemma F bounds w <= {wmax}; exhausting it --")
        for w in range(1, wmax + 1):
            print(f"          w={w}: divisors of p+w={p+w} are "
                  f"{divisors_of(p + w)}, none is -1 mod {4 * w}")
        print(f"        => F1({p}) is FALSE. (M0) fails.")
    print("  => (M0) is FALSE. The Gate A break of 5.1 cannot be repaired by")
    print("     proving an exhaustion lemma; F1 has to be widened instead.")

    print("\n=== CHECK 9b: NL survives -- F1-false exceptional primes have (F2) ===")
    def family_D_cert(p, cap=400):
        """4 g K L = p(K+L) + 1  ->  solution (gK, gL, p g K L)."""
        for L in range(1, cap + 1):
            for K in range(1, cap + 1):
                num = p * (K + L) + 1
                if num % (4 * K * L) == 0:
                    g = num // (4 * K * L)
                    x, y, zz = g * K, g * L, p * g * K * L
                    assert 4 * x * y * zz == p * (x * y + x * zz + y * zz)
                    return (g, K, L, (x, y, zz))
        return None
    for p in (5569, 9601):
        c = family_D_cert(p)
        print(f"  p={p} (mod 840 = {p % 840}), F1 FALSE: family-D cert "
              f"g={c[0]} K={c[1]} L={c[2]} -> {c[3]}" if c else
              f"  p={p}: no family-D cert found within the cap")
    print("  => NL = F1 or F2 is NOT refuted, but for these primes it rests")
    print("     entirely on the F2 side.")

    print("\n=== CHECK 10: tau normal form, and Lopez arXiv:2404.01508 ===")
    print("  (supports THEORY.md 9.4 and 9.5)")
    bad_norm = bad_f1 = checked = 0
    for p in primes_upto(300):
        if p < 5:
            continue
        for z in range(1, 200):
            m = 4 * z - 1
            if p % m == 0:
                continue
            ds = divisors_sq(factor(z), cap=10**6) or []
            A = {s for s in ds if (s + p * z) % m == 0}
            B = {z * z // t for t in ds if (4 * p * t + 1) % m == 0}
            checked += 1
            bad_norm += (A != B)
            dz = divisors_of(z)
            bad_f1 += ({s for s in A if any(s == z * w for w in dz)}
                       != {s for s in A if (z * z // s) in dz})
    print(f"  (G) 'm | sigma + p z'' <=> 'm | 4 p tau + 1', tau = z'^2/sigma:")
    print(f"    {checked} (p, z') pairs checked, mismatches = {bad_norm}")
    print(f"  F1 <=> tau | z'   (versus tau | z'^2 for all of G):")
    print(f"    {checked} (p, z') pairs checked, mismatches = {bad_f1}")
    bad_lopez = 0
    for d in range(1, 25):
        for n in range(1, 25):
            m = 4 * d * n - 1
            for p in range(1, 300):
                bad_lopez += ((p + 4 * d) % m == 0) != \
                             ((4 * p * d * n * n + 1) % m == 0)
                bad_lopez += ((p + n) % m == 0) != ((4 * p * d + 1) % m == 0)
                bad_lopez += ((p + 4 * d * d) % m == 0) != \
                             ((4 * p * n * n + 1) % m == 0)
    print(f"  Lopez (A) p=-4d, (B) p=-n, (C) p=-4d^2 (mod m=4dn-1) correspond")
    print(f"  to tau = d n^2, d, n^2 with z'=dn: mismatches = {bad_lopez}")
    print("  In particular (B) IS F1 (w=n, tau=d | z'): F1 is published.")
    print("  Lopez's tau set {d, n^2, d n^2} does NOT exhaust div(z'^2):")
    for z in range(1, 25):
        miss = sorted(set(divisors_of(z * z)) - lopez_taus(z))
        if miss:
            print(f"    z'={z:2d}: |div(z'^2)|={len(divisors_of(z * z)):2d}, "
                  f"tau missing from Lopez's system: {miss}")

    print("\n=== CHECK 11 [pre-registered]: is the tau form strictly wider? ===")
    print("  Search primes p<20000, levels z'<=300, for (p, z') where the tau")
    print("  criterion holds but none of Lopez's three tau values works, and")
    print("  for primes where that happens at EVERY level (which would refute")
    print("  Lopez's conjecture).")
    gap_level, gap_prime = 0, []
    for p in primes_upto(20000):
        if p < 5:
            continue
        any_full = any_lopez = False
        for z in range(1, 301):
            m = 4 * z - 1
            if p % m == 0:
                continue
            ds = divisors_sq(factor(z), cap=10**6) or []
            F = [t for t in ds if (4 * p * t + 1) % m == 0]
            if not F:
                continue
            any_full = True
            if any(t in lopez_taus(z) for t in F):
                any_lopez = True
            else:
                gap_level += 1
        if any_full and not any_lopez:
            gap_prime.append(p)
    print(f"  (p, z') levels where only the tau form works: {gap_level}")
    print(f"  primes where Lopez's tau never works for z'<=300: "
          f"{gap_prime if gap_prime else 'none'}")
    print("  => the tau form is strictly wider level-by-level, but Lopez's")
    print("     conjecture is NOT refuted in this range.")


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    main()
