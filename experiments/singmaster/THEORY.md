# THEORY — Singmaster's conjecture: the elliptic window is exhaustible, the record barrier reduces to frontier curves X_{k,l}, l ≥ 5, and the exact point where every known method stops

Target claim: `problem:singmaster` (research/math-problems.json) — bounded
multiplicity in Pascal's triangle; max known multiplicity 6 (entry 3003).
Scope: a semantic proof attempt along the attack line "multiplicity across
different columns requires C(n,k) = C(m,l) with k ≠ l — algebraic curves":
for fixed pairs (k,l) with k < l ≤ 4 I derive explicit birational models,
classify their genus, identify exactly which pairs could in principle
contribute beyond the known examples, and state a precise conjecture of the
requested form "multiplicity beyond the record requires an integral point on
a frontier curve". Auxiliary numerics: `aux_check.py`, `aux_check2.py`
(transcript `run_output.txt`) — boundary confirmations only, no search-bound
contribution.

Provenance conventions: **[proved here]** = proof or checkable derivation
below; **[verified numerically]** = confirmed by the auxiliary scripts;
**[classical, unverified]** = recalled from the literature, attribution and
exact statement not re-checked this session; **[my assessment]** = judgement
not backed by a checked source.

---

## 1. Definitions, conventions, known partial results

### 1.1 Multiplicity conventions

Work in the canonical half-triangle: a representation of N is a pair (n,k)
with 1 ≤ k ≤ n/2 and C(n,k) = N. Define

- μ_raw(N) = #{(n,k) : 0 ≤ k ≤ n, C(n,k) = N}  (full triangle),
- μ_int(N) = #{(n,k) : 2 ≤ k ≤ n−2, C(n,k) = N}  (interior positions only),
- K(N) = {k ≥ 2 : ∃n, C(n,k) = N, k ≤ n/2}  (canonical interior columns hit),
- ν(N) = |K(N)|.

Each canonical rep with k < n/2 contributes 2 raw positions; k = n/2
contributes 1; the column-1 rep (N,1) contributes 2. Hence

    μ_raw(N) = 2 + Σ_{canonical interior reps} (2 or 1),   μ_int(N) ≤ 2ν(N).

**[verified numerically]** (aux_check2 (h)): 3003 has canonical reps
{(3003,1), (78,2), (15,5), (14,6)}, so μ_raw(3003) = 8, μ_int(3003) = 6,
ν(3003) = 3. The claim card's "maximum known multiplicity 6" is μ_int;
under raw counting the record is 8. Nothing below depends on the convention;
the cleanest invariant is ν(N).

**Conjecture S (Singmaster, strong folklore form).** ν(N) ≤ 3 for all N ≥ 1
(equivalently μ_raw(N) ≤ 8, with 3003 expected to be the unique maximizer).
Singmaster's original conjecture is the qualitative statement
sup_N μ_raw(N) < ∞ [classical, unverified — exact phrasing].

### 1.2 Known partial results

- **Singmaster (1971): μ_raw(N) = O(log N)** [classical, unverified]. The
  argument combines Lemma 3 below (columns containing N have index
  k ≲ log₂ N) with a gap argument showing each column index can occur only
  O(1) times along the chain of nested gaps. This remains, to my knowledge,
  the best published unconditional bound; I know of no confirmed uniform
  improvement [my assessment].
- **Erdős–Selfridge (1975):** a product of two or more consecutive positive
  integers is never a perfect power [classical, unverified]. Since
  k!·C(n,k) = n(n−1)···(n−k+1), this kills any parametric family of
  collisions in which the common value is forced to be a perfect power, and
  is the standard tool for ruling out "structured" infinite families.
- **Ljunggren-type results:** the equation C(n,2) = C(m,3) (equivalently
  triangular = tetrahedral numbers) has, beyond the degenerate and
  same-row solutions, exactly the solutions giving 120, 1540, 7140
  [classical, unverified as to attribution; the solution set itself is
  confirmed inside our search boxes, see §6]. This is the model case of
  "one pair (k,l) = one elliptic curve, completely solved".
- **Heuristic finiteness [folklore, unverified]:** under the standard
  probabilistic model (probability that C(n,k) = C(m,l) for random n,m is
  ≈ 1/|C(n,k)|^{1−k/l} summed over scales), the expected total number of
  interior collisions is finite; i.e. the complete list of coincidences may
  be essentially the known one. This is a heuristic, not a theorem — but it
  calibrates what a proof must beat: not "many collisions" but
  "finitely many, each on its own curve".

---

## 2. The attempted lemma chain

### 2.1 Reduction to a countable family of curves

**Lemma 1 (symmetry is the only same-row coincidence). [proved here]**
If C(n,k) = C(n,l) with k < l then l = n − k.
*Proof.* The ratio C(n,k+1)/C(n,k) = (n−k)/(k+1) is strictly decreasing in k
on [0, (n−1)/2], so C(n,k) is strictly increasing there and strictly
decreasing after n/2; equality at distinct k,l forces {k,l} = {k, n−k}. ∎

Consequence: every genuine multiplicity is cross-row, and quotienting by the
involution k ↦ n−k is lossless. This is why K(N), not raw position counting,
is the right invariant.

**Lemma 2 (uniqueness within a column; curve decomposition). [proved here]**
For fixed k ≥ 1, n ↦ C(n,k) is strictly increasing on n ≥ k (ratio
(n+1)/(n+1−k) > 1). Hence for each N and k there is at most one n, and

    ν(N) ≤ 1 + #{(k,l) : 2 ≤ k < l ∈ K(N)},

i.e. multiplicities are exactly simultaneous integral points across the
family of affine curves

    X_{k,l} :  C(x,k) = C(y,l),   2 ≤ k < l,   (x,y) ∈ Z²,  x > l.

Each N with ν(N) = r produces C(r,2) points on the pairwise curves X_{k,l},
(k,l) ⊂ K(N)², all with the same y-value ("common-value condition").

### 2.2 Height of the columns containing N

**Lemma 3 (column index bound). [proved here]**
If (n,k) is a canonical rep of N then C(n,k) ≥ (n/k)^k ≥ 2^k, so
k ≤ log₂ N.
*Proof.* C(n,k) ≥ (n/k)^k by the standard product lower bound; n ≥ 2k on
canonical reps. ∎

So the family relevant to N is {(k,l) : l ≤ log₂ N} — O((log N)²) curves.
Together with Singmaster's gap argument this recovers μ_raw(N) = O(log N)
[the gap half is classical, unverified]. Note the shape of the problem this
exposes: **the set of curves that can carry N grows with N.** This is the
seed of the obstruction in §3.

### 2.3 Genus classification of the family X_{2,l} and the elliptic window

**Lemma 4 (hyperelliptic models for column 2). [proved here]**
For l ≥ 3, X_{2,l} is birational over Q to the hyperelliptic curve

    H_l :  W² = f_l(m) := 8·P_l(m) + (l!)²,   P_l(m) = m(m−1)···(m−l+1),

via w := 2n−1, W := l!·w, because C(n,2) = C(m,l) ⟺ (2n−1)² = 8C(m,l)+1.
The polynomial f_l is monic of degree l and squarefree for 3 ≤ l ≤ 30
**[verified numerically]** (aux_check2 (k); the gcd of f_l and f_l' is the
constant 8). Hence the normalization of H_l has genus ⌊(l−1)/2⌋. In
particular:

| pair | genus | status |
|---|---|---|
| X_{2,3} | 1 | solved classically (Ljunggren-type; values 120, 1540, 7140) [classical, unverified attribution] |
| X_{2,4} | 1 | explicit model below; exhaustion pending, routine with current algorithms |
| X_{2,5}, X_{2,6} | 2 | Faltings-finite; hyperelliptic Chabauty feasible per curve |
| X_{2,l}, l ≥ 7 | ≥ 3 | Faltings-finite, ineffective |

**Proposition 5 (explicit elliptic models for the rest of the window).**
[proved here as derivations; numerically confirmed on all hits in range]

(i) **X_{2,4}.** With u = 2m−3, w = 2n−1, the equation C(m,4) = C(n,2) is
equivalent to the quartic model

    u⁴ − 10u² + 57 = 48 w².

Moreover, with A := m² − 3m it is equivalent to the smooth intersection of
two quadrics

    (A+1)² − 3w² = −2,   B² = 4A + 9  (B = u²),

a genus-1 curve: the first equation is a Pell conic, and X_{2,4} is its
fiber product with y² = 4A+9 — which is exactly why the naive "it's a Pell
equation" impression is wrong: the square condition B = m²−3m +… being a
perfect square is what makes the curve genus 1 rather than 0.
*Derivation.* (2m−3)² = 4A+9 and (2m−3)⁴ − 10(2m−3)² + 57 = 16(A+1)² + 32,
so the quartic model reads 16(A+1)² + 32 = 48w², i.e. (A+1)² − 3w² = −2. ∎
**[verified numerically]** on every hit m ≤ 1500 (aux_check2 (e)).

(ii) **X_{3,4}.** With s = x−1, u_y = 2m−3, v = (u_y²−5)/4 ∈ Z, the equation
C(x,3) = C(m,4) is equivalent to the Mordell curve

    E :  v² = 4s³ − 4s + 1.

*Derivation.* y(y−1)(y−2)(y−3) = (u_y²−9)(u_y²−1)/16; equating to
24·C(x,3) = 4(s³−s)·6/… and completing squares in u_y² gives
(u_y² − 5)² = 16(4s³ − 4s + 1). ∎ **[verified numerically]** on every hit
m ≤ 2500; the only hit is the diagonal (x,m) = (7,7), value 35, giving
(s,v) = (6,29) — which is the reflection-symmetric point, not a genuine
collision.

(iii) **E is a quadratic twist of the conductor-37 curve 37a1.** Short
Weierstrass form Y² = X³ − X + ¼ (Y = v/2) has
j(E) = 110592/37 **[computed here]**, equal to j(37a1 : y²+y = x³−x)
**[verified numerically]**. The point P = (s,v) = (6,29) has infinite
order: kP ≠ O for k = 2..12, and E has no Q-rational 2-torsion (the cubic
X³−X+¼ has no rational root), so Mazur's torsion list leaves no possible
finite order **[verified numerically]**. Hence rank E(Q) ≥ 1 and X_{3,4}(Q)
is infinite — but by Siegel th. X_{3,4}(Z) is finite, and its determination
is a bounded, currently routine computation (elliptic logarithms /
Stoll--rest bounds; mwrank/Magma). All integral points found in a large box
are the degenerate ones (s ∈ {0,1,2}) and the diagonal (6,±29)
**[verified numerically, s ≤ 2·10⁵]**.

**Summary of §2.3:** every pair with k < l ≤ 4 is elliptic. There is no
genus ≥ 2 obstruction anywhere in the low window; the window is, in
principle, fully exhaustible with published algorithms.

### 2.4 The record barrier, and which pairs could beat it

**Hypothesis H_E (elliptic window exhausted).** The proper integral points
are exactly:
- X_{2,3}: (m,n) ∈ {(10,16), (22,56), (36,120)} — values 120, 1540, 7140
  (plus same-row/degenerate);
- X_{2,4}: (m,n) = (10,21) — value 210 (plus same-row (6,6));
- X_{3,4}: none beyond the diagonal (7,7).

**Proposition 6 (record barrier reduces to frontier curves). [proved here,
conditional on H_E]**
If ν(N) ≥ 4, then N lies on X_{k,l} for some pair 2 ≤ k < l with l ≥ 5.
*Proof.* Four interior columns span ≥ 3 collision pairs. By H_E the only
values realized on curves inside the window {l ≤ 4} are
{120, 210, 1540, 7140} (columns ⊂ {2,3} ∪ {2,4}) and the diagonal 35, and
none of these values lies on any third interior column: directly,
C(m,4) ∈ {120,1540,7140} has no solution, C(m,5) = 210 has none, and 35 is
a same-row value **[verified numerically in range; the H_E part is
conditional]**. Hence a 4-column N must use a pair with l ≥ 5. ∎

This is exactly the requested conjecture-form statement, and I state it as
the main output of this attempt:

> **Conjecture S\* (curve criterion for record-beating).** Every N with
> ν(N) ≥ 4 — i.e. every counterexample to μ_int ≤ 6 / μ_raw ≤ 8 — is an
> integral point of X_{k,l} for at least one pair 2 ≤ k < l, l ≥ 5, and
> simultaneously lies on two further curves X_{·,·} with a common value.
> Equivalently: to beat the record you must produce a new integral point on
> a genus ≥ 2 frontier curve (first candidates X_{2,5}, X_{2,6}, X_{3,5},
> X_{5,6}, …) *and* match it against two more columns.

Known points already on frontier curves **[verified numerically]**:
X_{2,5} ∋ 3003 = C(15,5), 11628 = C(19,5); X_{2,6} ∋ 3003 = C(14,6);
X_{2,8} ∋ 24310 = C(17,8). So frontier curves are *not* empty — the record
3003 itself lives on two of them. What is conjectured empty is the
**simultaneous** realization on ≥ 4 columns.

**Observation 7 (all known collisions involve column 2). [verified
numerically in boxes; literature completeness unverified]**
The known interior-collision values are 120:{2,3}, 210:{2,4}, 1540:{2,3},
3003:{2,5,6}, 7140:{2,3}, 11628:{2,5}, 24310:{2,8}. Every one hits column 2,
and the only known coincidence between two interior columns both ≥ 3 is
C(15,5) = C(14,6) (the 3003 pair). If that empirical law is a theorem, the
whole conjecture reduces to the hyperelliptic family {X_{2,l}}_{l ≥ 5},
where Baker-type effective methods do exist per curve.

---

## 3. Exactly where the chain breaks

**Break point B1 (technical, passable):** H_E is not yet a theorem in this
write-up. X_{2,3} is classical; X_{2,4} and X_{3,4} reduce to explicit
elliptic curves whose integral points are computable by published
algorithms (§2.3). This is engineering, not a fundamental barrier — but it
must be done before Proposition 6 is unconditional. (Status in the
literature of X_{2,4} in particular is likely settled somewhere I did not
re-check [classical, unverified].)

**Break point B2 (fundamental): uniformity across the family.** Grant B1.
Then Proposition 6 confines record-beaters to the union
𝒳 = ⋃_{l ≥ 5} ⋃_{2 ≤ k < l} X_{k,l}. Faltings/Siegel say each X_{k,l}(Z)
is finite — but the union is over ~(log N)² curves at height N, and:

1. Faltings is ineffective; it yields no computable list per curve.
2. Even an effective per-curve method (hyperelliptic Chabauty, Baker-type
   bounds) needs hypotheses (rank < genus) that are unchecked curve by
   curve, and — decisively — **finiteness per curve does not bound
   sup_N ν(N)**: N can grow, sample one new point off each of ~log²N
   curves, and every per-curve statement is consistent with ν(N) → ∞.
3. The available uniformity machinery does not reach: uniform Chabauty
   (KRZ/Stoll-type) bounds #X(Q) in terms of genus *and Mordell–Weil
   rank*, and rank is uncontrolled across 𝒳; the bounds concern rational
   points, far weaker than needed; and no theorem constrains two distinct
   curves X_{k,l}, X_{k',l'} from *sharing a value* — which is the actual
   content of ν(N) ≥ 4.

**Break point B3 (structural: why no bounded-dimensional object helps).**
k enters C(n,k) as the *degree* of the polynomial P_k(n), not as an
algebraic coordinate. "N occupies columns k, l, m" is therefore not a fiber
condition on any variety of bounded dimension independent of N; the
problem is intrinsically a countable union of curves. Consequently even the
standard uniformity conjectures (Bombieri–Lang, Uniformity of Rational
Points) do not formally imply Singmaster's conjecture **[my assessment]**.
What is missing is a *uniform common-value theorem* for polynomial families
of unbounded degree — an object with no existing theory.

**Why convexity/monotonicity cannot pass B2 (the anticipated negative
answer).** For fixed N let n_k(N) be the unique real root of C(·,k) = N
(Lemma 2 guarantees uniqueness). Stirling gives n_k(N) ≈ (k/e)·N^{1/k}·
(2πk)^{1/2k}, a smooth monotone-ish profile; for N = 3003 it passes through
n₂ = 78, n₅ = 15, n₆ = 14 — integrality at three points is pure accident,
and nothing in the order structure of k ↦ n_k(N) prevents integrality at
four. Worse, per-curve emptiness at large l is *false*: X_{2,5} and X_{2,8}
have genuine sporadic points (11628, 24310) **[verified numerically]**. So
the only route is bounding *simultaneous* integrality — an arithmetic
condition, unreachable by monotonicity, convexity, or gap arguments alone.

---

## 4. Minimal new lemmas that would unblock the chain

In increasing order of ambition; the first two are concrete, the third is
the fundamental one.

**(M1 — finish the window; feasible now).** Determine X_{2,4}(Z) and
X_{3,4}(Z) completely. Both are elliptic with explicit models (Prop. 5);
X_{3,4} is a twist of 37a1 with rank ≥ 1, so Siegel-finiteness is effective
via elliptic logarithms. This upgrades H_E to a theorem and makes
Proposition 6 unconditional: *any* future record-beater provably lives on
frontier curves with l ≥ 5.

**(M2 — first frontier curve).** Solve X_{2,5}: the genus-2 curve
W² = 8·m(m−1)(m−2)(m−3)(m−4) + 14400, with known points m ∈ {15, 19}
(values 3003, 11628). Hyperelliptic Chabauty (conditional on rank J(Q) < 2)
plus a Mordell–Weil sieve is a realistic computation. A complete solution
would either produce a new collision value or prove the only column-2
collisions at l = 5 are the known two.

**(M3 — the fundamental input: an anti-concentration lemma).**
The minimal new statement that unblocks the *global* conjecture is:

> **Lemma target (uniform anti-concentration).** There is an absolute
> constant A such that for every N,
> #{(k,l) : 2 ≤ k < l, N ∈ π(X_{k,l}(Z))} ≤ A,  where π(x,y) = C(x,k).

A natural, much weaker stepping stone that already collapses the family to
hyperelliptic curves (where effective methods exist per curve):

> **Lemma target (column-2 capture).** Every N with ν(N) ≥ 3 satisfies
> 2 ∈ K(N).

Column-2 capture + Proposition 6 would give: any record-beater is caught on
{X_{2,l}}_{l≥5}, a single-indexed hyperelliptic family with genus ⌊(l−1)/2⌋
→ ∞ — still not a proof, but a one-parameter problem where Baker--type
ineffective-to-effective technology and the Erdős–Selfridge/Saradha
machinery have the right shape. I know of no mechanism for M3 beyond
heuristics: the p-adic/Lucas constraints (C(n,k) mod p depends only on
digits) are far too weak to pin k, and the empirical evidence (Observation
7) is all the support there is.

---

## 5. Verdict: OBSTRUCTION-IDENTIFIED

Justification:

- **The route is live in the low window.** All pairs k < l ≤ 4 are
  elliptic with explicit birational models derived here (quartic /
  biquadratic Pell-fiber for (2,4); Mordell curve ≅ twist of 37a1, rank ≥ 1,
  for (3,4)) [proved here + verified numerically]. Exhausting them (M1) is
  a bounded computation with published methods and would make the record
  barrier (Prop. 6) a theorem: no integer with ν ≥ 4 can avoid the frontier
  family l ≥ 5.
- **The obstruction is precisely identified and is not the curves
  themselves.** It is the absence of any uniform control on integral points
  *and shared values* across the unbounded-degree family {X_{k,l}} (B2),
  with the structural reason that k lives in the degree, so no
  bounded-dimensional variety — and no standard uniformity conjecture —
  captures the problem (B3).
- **Not DEAD-END:** the strong conjecture ν(N) ≤ 3 is equivalent to a clean
  falsifiable statement (Conjecture S\*), each piece except the
  anti-concentration step is within reach of current effective methods, and
  the stepping stone "column-2 capture" would reduce the global problem to
  a single hyperelliptic family where the classical effective toolkit
  (Baker, Erdős–Selfridge, hyperelliptic Chabauty) applies curve by curve.
- **Not ROUTE-LIVE (for the full conjecture):** no existing or conjectural
  standard machinery (Faltings, uniform Chabauty, Bombieri–Lang) passes B2;
  a genuinely new type of input (M3) is required. Per the repo policy,
  SUPPORT-style progress here means: M1 and M2 are the next falsification
  stages, each with pre-registerable criteria (complete point lists on
  X_{2,4}, X_{3,4}, then X_{2,5}).

---

## 6. Auxiliary computations (boundary confirmations only)

- `aux_check.py` — canonical forms k!·C(n,k) = falling factorials;
  multiplicity box scan (rows ≤ 800, values < 10¹²): values with ≥ 2
  canonical interior reps are exactly {120, 210, 1540, 3003, 7140, 11628,
  24310}, and 3003 is the unique value with ≥ 3; the triple-{2,3,4}
  simultaneous system has no solution with N ≥ 2 up to x ≤ 2·10⁵.
- `aux_check2.py` (transcript `run_output.txt`) —
  (e) birational models of X_{2,4} (quartic and biquadratic forms) and
  X_{3,4} (Mordell form) verified on every hit in range;
  (f) integral points of E up to s ≤ 2·10⁵ are only the degenerate ones
  and the diagonal (6,±29);
  (g) j(E) = 110592/37 = j(37a1);
  (h) 3003: 4 canonical reps, 8 raw positions, 6 interior raw (the claim
  card's "6");
  (i) P = (6,29) has infinite order on E (kP ≠ O for k ≤ 12, no 2-torsion);
  (j) sweep of X_{2,l}, l ≤ 16, m ≤ 4000 — sporadic points only at the
  known values; row-reflections reappear at l = n−k as predicted by
  Lemma 1;
  (k) f_l = 8·P_l + (l!)² is squarefree for 3 ≤ l ≤ 30, confirming the
  genus formula ⌊(l−1)/2⌋.

None of these scans constitutes a search-bound contribution: each is a
finite-range confirmation of a lemma stated above, and every unbounded
claim is marked [classical, unverified] or [my assessment] in the text.
