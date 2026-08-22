# AUXILIARY script 2 -- boundary confirmation ONLY (see THEORY.md section 6).
# (e) verify birational models of X_{2,4} and X_{3,4} on all hits in range
# (f) integral-point probe on E: v^2 = 4s^3 - 4s + 1
# (g) j-invariant of E vs 37a1
# (h) multiplicity conventions for 3003
# (i) infinite-order check for P=(6,29) on E (group law over Q)
# (j) sweep of X_{2,l} sporadic points, l<=16, m<=4000
# (k) squarefree-ness of hyperelliptic models f_l = 8*P_l + (l!)^2, l<=30
from math import comb, isqrt
from fractions import Fraction as F

# (e)
for m in range(4, 1500):
    V = comb(m, 4)
    r = isqrt(8 * V + 1)
    if r*r == 8*V+1 and r % 2 == 1:
        n = (r+1)//2
        u, w = 2*m-3, 2*n-1
        assert u**4 - 10*u**2 + 57 == 48*w*w, (m,n)
        A = m*m - 3*m
        assert (A+1)**2 - 3*(2*n-1)**2 == -2
print("(e) X_{2,4}: quartic u^4-10u^2+57=48w^2 and biquadratic (A+1)^2-3w^2=-2,"
      " B^2=4A+9 verified on all hits m<=1500")
hits34 = []
for m in range(4, 2500):
    V4 = comb(m, 4)
    lo, hi = 4, 4*m
    while lo < hi:
        mid = (lo+hi+1)//2
        if comb(mid,3) <= V4: lo = mid
        else: hi = mid-1
    if comb(lo,3) == V4:
        s = lo - 1
        uy = 2*m - 3
        v = (uy*uy - 5)//4
        assert v*v == 4*s**3 - 4*s + 1, (lo,m)
        hits34.append((comb(lo,3), lo, m))
print("(e) X_{3,4}: Mordell model v^2=4s^3-4s+1 verified on hits m<=2500:", hits34)

# (f)
pts = [(s, isqrt(4*s**3-4*s+1)) for s in range(0,200001)
       if isqrt(4*s**3-4*s+1)**2 == 4*s**3-4*s+1]
print("(f) E integral points s<=200000:", pts)

# (g)
a, b = F(-1), F(1,4)
j_E = F(1728)*(4*a**3)/(4*a**3+27*b**2)
print("(g) j(E) =", j_E, "== j(37a1) =", F(48**3,37), ":", j_E == F(48**3,37))

# (h)
reps = set()
for k in range(1,9):
    n = 2*k
    while comb(n,k) <= 3003:
        if comb(n,k)==3003: reps.add((n,k))
        n += 1
reps.add((3003,1))
raw = sum(2 if y < x-y else 1 for x,y in reps)
interior_raw = sum(2 if (y < x-y and y >= 2) else 0 for x,y in reps)
print("(h) 3003 canonical reps:", sorted(reps), "| raw positions:", raw,
      "| interior raw:", interior_raw, "| canonical:", len(reps))

# (i)
def add(P,Q,a=F(-1)):
    if P is None: return Q
    if Q is None: return P
    x1,y1=P; x2,y2=Q
    if x1==x2 and y1==-y2: return None
    lam = (y2-y1)/(x2-x1) if P!=Q else (3*x1*x1+a)/(2*y1)
    x3 = lam*lam-x1-x2
    return (x3, -(y1+lam*(x3-x1)))
P=(F(6),F(29,2)); R=P
ok=True
for i in range(2,13):
    R=add(R,P)
    if R is None: ok=False; break
print("(i) P=(6,29/2) on Y^2=X^3-X+1/4 has kP != O for k=2..12:", ok,
      "-> P non-torsion (no 2-torsion over Q; Mazur odd orders 3,5,7,9,11 excluded)")
print("    2P =", add(P,P))

# (j)
print("(j) X_{2,l} points (V,m,n), C(m,l)=C(n,2), m<=4000, 3<=l<=16 "
      "(row-reflections of col-k hits reappear at l=n-k):")
for l in range(3,17):
    hits=[]
    for m in range(l, 4001):
        V=comb(m,l)
        r=isqrt(8*V+1)
        if r*r==8*V+1 and r%2==1:
            n=(r+1)//2
            if not (n==m): hits.append((comb(m,l),m,n))
    print(f"   l={l}: {hits}")

# (k)
import sympy as sp
x=sp.Symbol('x')
bad=[]
for l in range(3,31):
    Pp=sp.prod(x-i for i in range(l))
    f=sp.expand(8*Pp+sp.factorial(l)**2)
    g=sp.gcd(f, sp.diff(f,x))
    if g != 1 and sp.degree(g)>0: bad.append(l)
print("(k) f_l = 8*prod(x-i)+ (l!)^2 squarefree for 3<=l<=30:",
      not bad, ("offenders: "+str(bad) if bad else ""))
