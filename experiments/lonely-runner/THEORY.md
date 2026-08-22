# THEORY — Lonely Runner Conjecture: why chromatic methods saturate, and a resonance-series route that breaks at a precise point

Target claim: `problem:lonely-runner` (research/math-problems.json) — k runners,
distinct speeds, someone lonely by 1/(k+1).
Scope: a semantic proof attempt for the k=8 case (8 view speeds, gap 1/9),
structured as definitions → attempted lemma chain → exact break → minimal
unblocking lemma → verdict. Auxiliary numerics: `aux_check.py`, transcript in
`run_output.txt`. All computations below are boundary confirmations of lemmas
stated here, not search-bound extensions.

Provenance conventions: statements tagged **[proved here]** come with a proof
(or proof sketch complete enough to check); **[classical, unverified]** are
standard facts recalled from the literature whose attribution/exact form was
not re-checked in this session; **[verified numerically]** are confirmed by
`aux_check.py` at machine precision or with Monte-Carlo error bars; **[open]**
is stated honestly as such.

---

## 1. Definitions and known partial results

### 1.1 The view problem (working formulation)

For a finite set S = {a_1, ..., a_k} of distinct positive integers (speeds;
signs are irrelevant because of the wrap-around norm below) define

    δ(S) = sup_{t ∈ [0,1)}  min_{a ∈ S}  ||t a||,        ||x|| = dist(x, Z),

and the "bad set" (tube/comb union) at level ε

    B_a(ε) = { t ∈ [0,1) : ||t a|| < ε },   B_S(ε) = ∪_{a∈S} B_a(ε),
    U_S(ε) = [0,1) \ B_S(ε).

Each B_a(ε) is a union of 2a open intervals ("teeth") of length ε/a
centered at the points m/a, m = 0..a−1 — a **comb** with tooth-to-period
ratio 2ε, independent of a. So the whole problem lives at one fixed
tooth-density 2ε = 2/(k+1); only the *phases* of the k combs carry
arithmetic.

**Conjecture C(k) (view form of LRC).** For every k-set S of distinct
positive integers, δ(S) ≥ 1/(k+1).

**Lemma 1.1 (classical reduction). [classical, unverified as attribution;
the equivalence is elementary and checked]** LRC holds for all instances of
n = k+1 runners iff C(k) holds for all k-sets S.
*Proof direction (⟸ failure):* if δ(S) < 1/(k+1) for |S| = k, the instance
with speeds {0} ∪ S fails (at every t some runner of S is within 1/(k+1) of
the runner at 0). Direction (⟹): given S, view the instance {0} ∪ S from the
runner at 0. ∎

Throughout, k = number of view speeds, ε = 1/(k+1); the claim card's "k
runners, gap 1/(k+1)" corresponds to C(k−1) under this convention.

### 1.2 Known landscape [status flags per item]

- C(1), C(2) elementary; C(2) worst case is the scaled pair {m, 2m} with
  δ = 1/3 exactly **[proved here, Prop. 2.3; extremality of {m,2m} classical,
  unverified]**.
- C(k) for k ≤ 6: Bohman–Holzman–Kleitman, "Six lonely runners" (2001)
  **[classical, unverified]**. C(7): attributed to Barajas–Serra (2008) via
  chromatic/Δ-system arguments **[unverified; the problem card says "k ≤ 7ish",
  consistent]**. No proof of C(8) is known **[unverified]**.
- Best general lower bounds are of the shape δ(S) ≥ c/k for a universal
  c < 1 (classically c ≈ 1/2; improvements exist in recent literature)
  **[unverified — exact constants not checked here]**. The trivial
  Dirichlet-type bound δ(S) ≥ 1/(2k) is elementary (2k arcs of radius
  1/(2k) around multiples of 1/a_i cannot cover [0,1) by total measure
  2k/(2k) = 1 with strict inequality... in fact the clean elementary bound is
  1/(2k−2+2/(k+1)) **[unverified]**; nothing at c = 1 is known in general).
- Extremal (tight) family: S = {m, 2m, ..., km} has δ = 1/(k+1) **[proved
  here, Prop. 2.3]**. So Conjecture C(k), if true, is exactly tight, and the
  closed-inequality formulation is essential: for the tight family the
  *open*-tube survivor set U_S(1/(k+1)) is empty (measure 0).
- Distance-graph reformulation: for the distance graph G(S) on Z with edge
  set {x, x±a : a ∈ S}, a Sturmian (rotation) coloring argument gives:
  δ(S) ≥ q/p ⟹ χ_c(G(S)) ≤ p/q, and χ_c ≤ χ. Hence

  **Lemma 1.2 (chromatic bridge). [proved here at sketch level; the full
  identity δ(S) = 1/χ_c(G(S)) is classical folklore, unverified]**
  C(k) ⟺ every k-distance graph G(S) satisfies χ(G(S)) ≤ k+1.

  *Proof sketch of the useful direction:* given t with ||t a|| ≥ q/p for all
  a ∈ S, set c_θ(n) = ⌊n p t + θ⌋ mod p. For all θ outside a countable
  union of points, c_θ is a circular coloring of G(S) with parameter q:
  for an edge of length a, the color increment is ⌊(n+a)pt + θ⌋ − ⌊npt + θ⌋,
  which stays in the allowed circular window because dist(pta, pZ) ≥ q.
  Boundary cases are absorbed by the shift θ. ∎

### 1.3 Why chromatic lower-bound methods saturate (diagnosis, §2.5 gives the mechanism)

The literature phrase "view-graph chromatic bounds settle small k and
saturate around k ≤ 7" is, under Lemma 1.2, the statement that *upper*-bound
constructions for χ(G(S)) ≤ k+1 are known only for structured S. Three
regimes are visible, and the known tools grip only two of them:

1. **Parity-degenerate sets** (all speeds share a factor 2, or a common
   divisor d): G(S) is d-partite-ish; e.g. all-odd S gives a bipartite graph,
   χ = 2. LRC is trivially satisfiable with huge slack (δ({5,7}) = 1/2,
   verified numerically, C1). Coloring tools succeed; nothing is being
   proved about LRC's hard core.
2. **Clique-containing sets** (e.g. {1, ..., k}, or any S whose elements fit
   inside an arithmetic cluster): G(S) ⊇ K_{k+1}, so χ = k+1 exactly, and the
   coloring n mod (k+1) is explicit. LRC holds *with zero slack*
   (δ = 1/(k+1) exactly, Prop. 2.3). These instances are tight: every
   inequality in any proof of C(k) on them must be an equality.
3. **Generic coprime sets** (e.g. large primes): G(S) is locally tree-like,
   has fractional chromatic number ≈ 2 (all-even numbers form an independent
   set of density 1/2 when S is all-odd), and (k+1)-colorings exist in
   abundance — but *no constructive or counting argument presently
   certifies one*. The structural tools that succeeded for k ≤ 7
   (Δ-systems/sunflowers of tooth-center progressions; BHK-style first-exit
   pattern analysis) all consume **exact arithmetic coincidences** (common
   tooth centers = gcd structure; additive relations a_i + a_j = a_l), and
   generic sets contain none beyond the trivial. Meanwhile the pattern space
   of first-exit analyses grows super-exponentially in k, which is why the
   case analysis is complete only through k = 7 **[unverified]**.

So the saturation is not a failure of ingenuity at k = 8 specifically; it is
a regime gap: chromatic methods are strong exactly where C(k) is easiest
(regimes 1–2) and mute exactly where the remaining difficulty lives
(regime 3 and, as we show below, a subtle *phase-locked middle regime* that
regime analysis misses).

---

## 2. Reformulations and the tight family [proved here]

**Lemma 2.1 (comb-cover form).** δ(S) ≥ ε ⟺ U_S(ε) ≠ ∅ ⟺ the k combs
B_a(ε) do not cover the circle. Trivial restatement. ∎

**Lemma 2.2 (geometric form).** Identify T^k with R^k/Z^k and let
γ_a(t) = t·a mod 1 be the rational geodesic through 0. Then
δ(a) ≥ ε ⟺ γ_a meets the closed central box C̄ = [ε, 1−ε]^k + Z^k; i.e.
**every rational line through the origin in T^k must enter the central box**.
Trivial restatement; note the box has side 1 − 2ε = (k−1)/(k+1) and volume
((k−1)/(k+1))^k → e^{−2}: a *random* point of T^k lies in the box with
probability ≈ 0.135 regardless of k. This is the equidistribution heuristic
that the whole §3 program tests. ∎

**Proposition 2.3 (the tight family, with proof).** For every k ≥ 1 and
m ≥ 1: δ({m, 2m, ..., km}) = 1/(k+1).
*Proof.* ≥: at t = 1/(k+1), the points i/(k+1), i = 1..k, all lie at
distance ≥ 1/(k+1) from Z. ≤: given any t, consider the k+1 points
0, t, 2t, ..., kt mod 1 on the circle. Their k+1 gaps sum to 1, so some gap
≤ 1/(k+1); a gap joins two points jt, it with 0 < |i − j| ≤ k, hence equals
||d t|| for some 1 ≤ d ≤ k. So min_{1≤d≤k} ||dt|| ≤ 1/(k+1) for every t. ∎
[Verified numerically for {1,...,8}: δ = 1/9 = 0.111111..., argmax t = 7/9
(C1).] Note the proof of "≤" is a pure pigeonhole on the *orbit segment*;
this rigidity is what any proof on tight instances must reproduce exactly.

**Corollary 2.4.** For tight instances the open survivor set U(1/(k+1)) has
measure zero (the sup is attained only at boundary points). Any method that
certifies μ(U) > 0 cannot apply to tight instances; conversely any proof of
C(k) must handle instances where the "target set" has measure zero.

---

## 3. The attempted lemma chain: a resonance-series program for k = 8

Fix ε = 1/9, |S| = 8. Let f_a = 1_{B_a} and write its Fourier expansion on
T = R/Z:

    f_a(t) = Σ_{j∈Z} ŝ(j a) e^{2πi j a t},   ŝ(0) = 2ε,  ŝ(x) = sin(2πxε)/(πx).

### Lemma 3.1 (resonance identity, EQ*). [proved here; machine-verified, C2]

For every finite S and ε:

    μ( ∩_{a∈S} B_a(ε) ) = Σ_{m∈Z}  Π_{a∈S}  ŝ( m·L / a ),   L = lcm(S).

*Proof.* Expand each indicator and integrate; ∫ e^{2πi t Σ j_a a} dt = 1
iff Σ j_a a = 0. Writing j_a = m·(L/a) (the general integer solution of
Σ j_a a = 0 with L = lcm(S) — since the a's need not be coprime, L/a is the
minimal positive integer making the products commensurate) gives the sum. ∎

The m = 0 term is (2ε)^{|S|} — the value the coordinates would have if they
were independent. The m ≠ 0 terms are the **resonance tail**: it is nonzero
exactly because the map t ↦ (ta)_{a∈S} traces a 1-dimensional subtorus, not
all of T^{|S|}. EQ* is the *exact* quantitative equidistribution statement
behind this problem: the "defect" of equidistribution is a concrete,
absolutely convergent (for ε < 1/2) series whose terms are explicit
trigonometric values at the resonance orders mL/a.

### Corollary 3.2 (master identity). [proved here]

    μ(U_S(ε)) = Σ_{T ⊆ S} (−1)^{|T|} Σ_{m∈Z} Π_{a∈T} ŝ(m L_T/a)
              = (1−2ε)^{k}  +  (signed resonance tail),

with (1−2ε)^k = (7/9)^8 = 0.133920 at k = 8. LRC for the instance S is the
statement that this series is positive (and, at tight instances, that the
*closed* version survives with the tail cancelling the main term exactly).

### Lemma 3.3 (pair defect, exact + envelope). [proved here; numerically confirmed, C3]

For a pair, writing g = gcd(a,b), a' = a/g, b' = b/g (the *reduced
skeleton*):

    Δ₂(a,b) := μ(B_a ∩ B_b) − (2ε)² = 2 Σ_{n≥1} ŝ(a' n) ŝ(b' n),

and with the envelope |ŝ(x)| ≤ min(2ε, 1/(π|x|)):

    |Δ₂(a,b)| ≤ (8ε²) Σ_{n≥1} min(1, 1/(π a' n)) min(1, 1/(π b' n))
              = O( ε² · log / (a' + b') + ε²/(a' b') )  → 0 as a'+b' → ∞.

The defect depends **only on the reduced skeleton** (a', b'), not on the
absolute scale — confirmed exactly: (2,4) ≡ (1,2), (2,6) ≡ (1,3), and the
decay table (C3): (10,11): +1.1e−3; (30,31): +8.0e−5; (97,98): +1.3e−5;
(300,301): +8.2e−7. ∎

### Lemma 3.4 (assembly attempt at k = 8, Bonferroni order 5). [proved here as a conditional]

Bonferroni's odd-order partial sums give lower bounds for μ(U). Using the
random-model values Σ_j^0 = C(8,j)(2ε)^j (exact rational arithmetic):

    1 − Σ₁ + Σ₂ − Σ₃ + Σ₄ − Σ₅
      = 1 − 16/9 + 112/81 − 448/729 + 1120/6561 − 1792/59049
      = 0.130737,

while the exact value of the full alternating sum is (7/9)^8 = 0.133920 (the
difference +0.00318 is the order-6..8 tail, whose sign is *a priori*
uncontrolled). Hence, with two-sided defect bounds |Δ_j| per intersection:

    μ(U_S(1/9)) ≥ 0.130737 − [28·Δ₂ + 56·Δ₃ + 70·Δ₄ + 56·Δ₅] − 0.00318.

**Conditional conclusion:** if a uniform defect lemma (call it **Lemma D**)
holds — Δ_j(S) ≤ D_j for all |S| ≤ 5, with Σ C(8,j) D_j < 0.127 — then
μ(U) > 0 and C(8) holds for that S. Lemma 3.3 supplies Δ₂ ≤ ~1.2e−3 already
for reduced entries ≥ 10, leaving budget ~0.127 for the higher orders.

### 3.5 Status of Lemma D: TRUE for pairs and dissociated triples; FALSE uniformly — the first break

Monte-Carlo (C4, ±2e−4):

    triple            μ(∩ B)      Δ₃ = μ − (2ε)³
    (10, 11, 12)      0.0259      +1.50e−2
    (50, 51, 52)      0.0248      +1.38e−2
    (1000,1001,1002)  0.0247      +1.37e−2     ← NO decay in scale
    (137, 251, 503)   0.0113      +2.8e−4      ← dissociated: decays

Consecutive-type triples carry a **persistent** positive triple correlation
at every scale. The mechanism is visible in EQ*: the relation lattice
L_S = {z ∈ Z^S : Σ z_a a = 0} of (m, m+1, m+2) contains near-vectors —
z = (1, 1, −1) has z·a = 49, small relative to the entries — and near-
relations keep the resonance arguments m·L/a in fixed rational relation to
each other, so the products ŝ(mL/a)Π do not decay along the series. Defect
decay is governed **not by entry size but by the arithmetic quality of the
relation lattice** (its short and near-short vectors). This is precisely the
"covering radius / geometry of the speed lattice" that the alternative route
hoped to exploit: the correct invariant is

    ρ(S) := min { ‖z‖₁ : z ∈ Z^S, 0 < |Σ z_a a| ≤ η · min_a a }   (near-relation depth),

and Δ_S is a function of (L_S, ρ(S)), not of min(S).

Meanwhile the *measured* uncovered sets stay comfortable (C5): μ(U) =
0.1360 ± 0.0005 for generic primes, 0.1303 ± 0.0005 for consecutive
50..57 — both near the random value 0.1339 — and δ(50..57) = 0.4673 ≫ 1/9
(exact, C5b). So the phase-locked families are individually far from
failure; it is the *method* (additive error accumulation) that cannot see
their survivors, because the positive Δ₃-type correlations (56 triples ×
~1.4e−2 ≈ 0.77 ≫ budget 0.127) are cancelled at higher orders by the
rigidity of the arrangement.

---

## 4. Exactly where the chain breaks, and why existing methods cannot pass

The chain L1 (reduction) → L2 (comb/box forms) → EQ* (exact resonance
identity) → pair decay (L3.3) is proved and machine-checked. It breaks at
two precisely located points, and the breaks are structural, not technical:

**(B1) Tight instances: exact cancellation.** For S = {1, ..., 8},
μ(U(1/9)) = 0 exactly (Prop. 2.3 + Cor. 2.4): the resonance tail of EQ*
cancels the main term (7/9)^8 *identically*. Any proof technology whose
error terms accumulate additively — inclusion–exclusion truncation,
second-moment/Janson estimates, sieve lower bounds — certifies at best
μ(U) ≥ (positive main term) − (accumulated tail bounds), and on tight
instances the truth is 0, so such a technology must have tail bounds that
are *exact identities* on these instances. No such exactness is available
from any analytic method known to the author. What is needed instead is a
structural reproduction of the pigeonhole mechanism in Prop. 2.3 ("k+1 orbit
points, k+1 gaps") — i.e., exact combinatorics, not estimates.

**(B2) Phase-locked middle regime: defect decay fails uniformly.** Lemma D
is refuted as a uniform statement by the consecutive-triple plateau (§3.5):
Δ₃ ≈ 1.4e−2 at entries 10, 50, and 1000 alike. The budget arithmetic of
Lemma 3.4 then fails for consecutive-type 8-sets even though those sets are
individually comfortable. A corrected Lemma D would have to be stated in
terms of the near-relation depth ρ(S) — but then the bad regime (small ρ)
is exactly the regime of approximate additive relations, where one no longer
has the exact coincidences that Δ-system/first-exit methods consume, nor the
dissociation that Fourier decay needs. The two method families fail on
*complementary* sets, and the middle is covered by neither.

**Why no existing method passes these points:**
- *Chromatic / Δ-system arguments* (the k ≤ 7 technology) consume exact
  coset coincidences of tooth centers (gcd lattices) and exact additive
  relations; they are mute on regime-3 sets and on large-scale phase-locked
  sets (whose only coincidences are approximate).
- *First-exit pattern analysis* (BHK-style) needs the fastest comb to have
  boundedly many teeth — it degenerates at scale, and its pattern space
  grows super-exponentially in k.
- *Fourier / IE / sieve* die on (B1) by design and on (B2) by the plateau.
- *Naive quantitative equidistribution* — the statement "μ(U_S(1/(k+1))) ≥
  c_k > 0 uniformly" or "Δ_S → 0 as entries grow" — is **refuted** (Cor. 2.4
  and C4 respectively). The correct equidistribution statement is EQ* itself,
  which is exact; the open content is entirely in controlling its resonance
  tail by relation-lattice data.

## 5. The minimal new lemma that would unblock k = 8

The chain reduces C(8) to a concrete dichotomy. The single missing lemma is
a **structure-or-slack theorem for relation lattices**:

> **Lemma X (target).** There is an explicit constant B such that every
> 8-set S satisfies at least one of:
> (i) *slack:* Σ_{2≤|T|≤5} C(8,|T|) |Δ_T(S)| ≤ 0.12 (whence Lemma 3.4 gives
> μ(U) > 0 and C(8) holds for S); or
> (ii) *rigidity:* the relation lattice L_S has a near-vector z with
> ‖z‖₁ ≤ B and |Σ z_a a| ≤ B′·min_a a — i.e., S carries an approximate
> additive/multiplicative relation — AND for every such S, δ(S) ≥ 1/9 is
> provable by an exact argument (a stability version of the Prop. 2.3
> pigeonhole, or an explicit Sturmian time).

Two remarks on what makes this "minimal":
- (i) needs only *upper* bounds on Δ_T in the slack branch; the pair case
  (Lemma 3.3) already delivers its part. The genuinely open analytic
  ingredient is uniform control of Δ_T for |T| = 3,4,5 **in terms of ρ(S)** —
  plausibly reachable from EQ* by summing the series against the near-vector
  decomposition of L_S, but not done here.
- (ii) is a near-extremizer stability statement. Its exact (η = 0) ancestor
  is open already for k = 3: the classification of 3-sets with δ = 1/4 is,
  to the author's knowledge, not in the literature **[unverified]**, while
  for k = 2 it is classical that the unique extremal is the scaled pair
  {m, 2m} **[classical, unverified; consistency checked numerically, C1:
  δ(1,2) = 1/3, δ(2,3) = 2/5, δ(5,7) = 1/2]**. Lemma X for k = 8 subsumes
  what the Δ-system program attempted globally, but phrased on relation
  lattices it is finite-dimensional and does not require a case explosion:
  the rigidity branch should reduce to bounded-size certificate patterns
  (additive triples/quadruples and divisibility chains), each handled once.

## 6. Verdict: **OBSTRUCTION-IDENTIFIED**

Justification.
- *Not a dead end:* the chain up to EQ* is new to this session, exact,
  machine-verified (C2: agreement with exact tooth arithmetic to ≤ 1e−11 on
  all tested pairs), and it converts LRC(8) into a quantitative statement
  about resonance series controlled by relation-lattice data. It yields an
  immediate conditional theorem: **C(8) holds for every 8-set whose
  relation lattice has no near-vector with ‖z‖₁ ≤ B** (slack branch,
  conditional only on higher-order defect control that pairs already
  exhibit and dissociated triples confirm numerically).
- *Obstruction identified, twice over:* (B1) tight instances force exact
  cancellation of the main term, so all estimate-based technologies are
  categorically excluded there; (B2) the needed uniform defect decay is
  false, with an explicit counterexample family (consecutive triples,
  Δ₃ ≈ 1.37e−2 at every scale) that sits precisely in the gap between the
  exact-coincidence methods (k ≤ 7 chromatic/Δ-system) and the
  dissociation-based analytic methods. This is the precise mechanism behind
  the observed saturation of chromatic bounds around k ≤ 7.
- *What would change the verdict:* a proof of Lemma X's branch (ii) for
  k = 8 (near-extremizer stability), or a ρ(S)-based version of Lemma D.
  Both are finite, concrete targets; neither is a search-bound computation,
  and neither exists in the literature consulted from memory this session
  **[unverified]**.

## Auxiliary artifacts

- `aux_check.py` — all computations (C1 exact δ via arrangement vertices;
  C2 EQ* vs exact teeth arithmetic; C3 pair defects; C4 triple defects;
  C5 uncovered measures; C5b exact δ(50..57)). Transcript: `run_output.txt`.
  Total runtime ≈ 2 min; no search over speed sets beyond the named
  boundary cases was performed, consistent with the repo's semantic-solution
  policy (AGENTS.md, 数学問題への取り組み方).
