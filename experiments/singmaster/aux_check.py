# AUXILIARY script -- boundary confirmation ONLY (see THEORY.md section 6).
# Purpose: (a) confirm canonical-form identities, (b) confirm known multiplicity-2
# values in a small box, (c) probe the triple-{2,3,4} system on its Mordell curve,
# (d) confirm the (2,4) Pell reduction. NOT a search-bound contribution.
from math import comb, isqrt

# --- (a) canonical forms: k!*C(n,k) = falling factorial P_k(n)
for n in range(2, 60):
    for k in (2, 3, 4):
        ff = 1
        for i in range(k): ff *= n - i
        assert k * comb(n, k) == ff if k == 2 else ff == [None, None, 2, 6, 24][k] * comb(n, k)
print("(a) canonical forms P_k(n)=k!*C(n,k) verified for n<60, k<=4")

# --- (d) Pell reduction for (k,l)=(2,4): C(m,4)=C(n,2) <=> (X+1)^2 - 3(2n-1)^2 = -2,
#         X = m^2-3m
hits = []
for m in range(4, 400):
    V = comb(m, 4)
    r = isqrt(8 * V + 1)
    if r * r == 8 * V + 1 and r % 2 == 1:
        n = (r + 1) // 2
        X = m * m - 3 * m
        assert (X + 1) ** 2 - 3 * (2 * n - 1) ** 2 == -2
        if 2 * 4 <= m: hits.append((V, m, n))
print("(d) (2,4) coincidences m<=400:", hits)

# --- (b) multiplicities in a box: rows n <= 800, canonical 2<=k<=n/2, values < 10**12
from collections import defaultdict
d = defaultdict(list)
for n in range(4, 801):
    for k in range(2, n // 2 + 1):
        v = comb(n, k)
        if v < 10**12:
            d[v].append((n, k))
multi = {v: locs for v, locs in d.items() if len(locs) >= 2}
print("(b) values with >=2 canonical reps (rows<=800, val<1e12):")
for v in sorted(multi):
    print("   ", v, multi[v])
triples = {v: locs for v, locs in d.items() if len(locs) >= 3}
print("(b') values with >=3 canonical reps:", triples)

# --- (c) triple {2,3,4}: need simultaneously
#       col2: 8N+1 = u^2 ; col3: 6N = x^3 - x ; col4: 24N+1 = v^2
#   eliminating N:  v^2 = 4x^3 - 4x + 1  (Mordell curve)  AND  3u^2 = 4x^3 - 4x + 3
sol = []
for x in range(1, 200001):
    w = 4*x**3 - 4*x + 1
    v = isqrt(w)
    if v*v != w: continue
    w3 = 4*x**3 - 4*x + 3
    if w3 % 3: continue
    u = isqrt(w3 // 3)
    if u*u == w3 // 3:
        N = (u*u - 1) // 8
        sol.append((x, u, v, N))
print("(c) triple-{2,3,4} system solutions x<=2e5:", sol,
      " -> N>=2 candidates:", [s[3] for s in sol if s[3] >= 2])

# --- columns of 3003 sanity
print("3003 canonical reps:", d.get(3003))
