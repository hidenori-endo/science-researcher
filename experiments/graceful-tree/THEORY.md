# THEORY — The Graceful Tree Conjecture: where leaf-induction breaks, and what would unblock it

**Target claim:** `problem:graceful-tree` (Ringel–Kotzig, 1967). Every tree with `m` edges admits a
graceful labeling: an injective `f: V → {0,…,m}` such that the edge labels `|f(u) − f(v)|` are exactly
`{1,…,m}`.

**Scope of this document.** This is a semantic proof attempt per AGENTS.md: definitions, a lemma chain,
the exact break point, and the minimal missing lemma. Computations are confined to
`aux_small_checks.py` (all free trees with ≤ 9 vertices) and are used **only** to confirm or refute
boundary cases of the lemmas; nothing below rests on search-bound extension.

---

## 1. Definitions and known partial results

### 1.1 Definitions

**Graceful labeling.** `T` a tree, `m = |E(T)|`. `f: V(T) → {0,…,m}` injective with
`{ |f(u) − f(v)| : uv ∈ E(T) } = {1,…,m}`. Since `T` has `m` edges and `m+1` vertices, a graceful
labeling uses **all** `m+1` available labels and **all** `m` edge labels: there is no slack of either
kind. This double-tightness is the source of every obstruction below.

**Slack-σ labeling.** For `M ≥ m` and `S ⊆ {1,…,M}` with `|S| = m`: an injection
`f: V(T) → {0,…,M}` with edge-difference set exactly `S`. Slack is `σ = M − m`. Graceful = slack-0 with
`S = {1,…,m}`.

**α-labeling (Rosa).** A graceful labeling of a bipartite tree with bipartition `(X, Y)` and a threshold
`λ` with `f(X) ⊆ {0,…,λ}`, `f(Y) ⊆ {λ+1,…,m}`.

**Observation 1.2 (threshold is forced; proof is mine).** In an α-labeling,
`|X| ≤ λ+1` and `|Y| ≤ m−λ`, and `|X| + |Y| = m+1 = (λ+1) + (m−λ)`, so both inequalities are equalities:
`f(X) = {0,…,λ}`, `f(Y) = {λ+1,…,m}`, and `λ = |X| − 1`. Consequently **every edge crosses the
threshold**, so adding a constant to all high-class labels shifts every edge label by exactly that
constant. This is the only known mechanism that translates edge-label sets, and it is exactly what
plain graceful labelings lack.

**Punctured labeling.** `c ∈ {1,…,m}`: an injection `f: V(T) → {0,…,m}` with edge-difference set
`{1,…,m} ∖ {c}`. (`T` has `m` edges, so one edge label of the full set is missing and one vertex label
is unused.) Iterating: `k`-punctured labelings have difference set `{1,…,m} ∖ C`, `|C| = k`.

**Compatible strip chain (CPC).** A sequence `T = T_0 ⊃ T_1 ⊃ … ⊃ T_m = {r}` where `T_{i+1} = T_i − ℓ_i`
for a leaf `ℓ_i` of `T_i`, together with injections `f_i: V(T_i) → {0,…,m}` such that `f_i` is `i`-punctured
(difference set `{1,…,m} ∖ C_i`, `|C_i| = i`) and the chain is **compatible**: for each `i`, the labels
`f_{i+1}` agree with `f_i` on `V(T_{i+1})`, and `f_i(ℓ_i) = f_{i+1}(p_i) ± c_i` where `p_i` is the parent
of `ℓ_i` in `T_i` and `C_{i+1} = C_i ∪ {c_i}`.

**Extendable leaf.** A leaf `ℓ` of `T` (parent `p`) such that `T − ℓ` admits a graceful labeling with
`f(p) = 0`.

### 1.2 Known partial results (literature; citations marked unverified where I could not check them here)

- Graceful/α-labelings introduced by Rosa (1967). **Caterpillars are graceful** (Rosa 1967; high
  confidence, standard). **Symmetrical trees** (Rosa 1967) and **olive trees** (Bermond–Brouwer–Germa)
  are graceful *[unverified citations]*.
- **Spiders** (one vertex of degree ≥ 3 with path legs) are graceful *[unverified citation; I recall a
  proof exists]*.
- Trees with few leaves, small diameter, or bounded branching are graceful in several partial results
  *[unverified citations]*. Machine verification of all trees up to roughly 29–35 vertices exists
  *[unverified]*.
- **Skolem sequences** (partitions of `{1,…,2n}` into pairs `(a_i, b_i)`, `b_i − a_i = i`) exist iff
  `n ≡ 0, 1 (mod 4)`; hooked Skolem sequences cover `n ≡ 2, 3 (mod 4)` *(standard; high confidence)*.
  Graceful labelings of stars and caterpillars are equivalent to Skolem-type objects: this is the
  prototype of what I call below the **zero-slack pairing technology**.
- It is known that graceful does **not** imply α-graceful *[unverified]*; the α-labeling analogue of the
  conjecture is not available as a strengthening.

---

## 2. The attempted lemma chain

**L1 (Extension Rigidity — proved).** *Let `T = T′ + ℓ` (`ℓ` a leaf, parent `p`, `|E(T′)| = m−1`). Let
`f: V(T′) → {0,…,m}` be injective with edge differences `{1,…,m−1}` (a 1-punctured labeling of `T′`).
Then `f` extends to a graceful labeling of `T` iff `f(p) ∈ {0, m}`.*

*Proof.* The extension must place `ℓ` at the unique unused label `x ∈ {0,…,m}`, and the new edge must
carry the unique missing label `m`: `|x − f(p)| = m` with both values in `{0,…,m}` forces
`{x, f(p)} = {0, m}`. ∎

**Corollary L1′.** If `T′` is labeled *gracefully* (labels `{0,…,m−1}`), extension requires `f(p) = 0`
(`f(p) = m−1` admits no partner `x` in `{0,…,m}`). So the naive Rosa induction needs the parent of the
re-attached leaf to sit at label 0 — a property with no known density guarantee.

**L2 (Affine Rigidity — proved).** *For any affine isometry `g(x) = ±x + c` of ℤ and any slack-σ
labeling `f` with difference set `S`, the composite `g ∘ f` is a slack-σ labeling with the same
difference set `S`.* Hence graceful edge-label sets are fixed points of the entire affine group:
**translation and reflection cannot make two graceful pieces' edge-label sets disjoint**
(`{1,…,m₁} ∩ {1,…,m₂} = {1,…,min(m₁,m₂)} ≠ ∅` for `m₁, m₂ ≥ 1`). ∎

**L3 (Budget Pigeonhole — proved).** *Let `T₁, T₂` have `m₁, m₂ ≥ 1` edges. In any graceful labeling of
a tree containing both as disjoint subtrees, the label sets of the two pieces intersect in exactly one
label; in particular no composition keeps either piece's own graceful labeling intact.*

*Proof.* A graceful labeling of the joined tree (`m₁+m₂` edges) has `m₁+m₂+1` labels for
`m₁+m₂+2` vertices, so by inclusion–exclusion `|f(V₁) ∩ f(V₂)| ≥ 1`. If instead `T₁`'s own graceful
labeling (which uses **all** of `{0,…,m₁}`) were kept intact, `T₂`'s `m₂+1` vertices would have to fit
into the `m₂` remaining labels `{m₁+1,…,m₁+m₂}` — impossible. The same count kills root-identification
and edge-join symmetrically. Moreover a *span* obstruction: a piece whose difference set is the interval
`{Δ+1,…,Δ+m′}` has vertex span ≥ `Δ+m′`, while the residual budget has width `m′`. ∎

**Consequence.** The α-mechanism of Observation 1.2 (uniform shift of edge labels) cannot be deployed by
shifting a sub-labeling: any valid composition **interleaves both pieces' vertex labels and splits
`{1,…,m}` into two prescribed complementary difference sets** — i.e., composition is a Skolem-type
pairing problem, not a label-shift argument. This, I claim, is the precise reason "graceful labelings of
`T₁, T₂` ⇒ graceful labeling of the join" has no elementary proof even for α-labelable pieces.

**L4 (VTE ⇒ GTC — proved as an implication; its hypothesis is FALSE).**
*If every tree with `m` edges and every vertex `v` admitted a graceful labeling with `f(v) = 0`
("vertex-transitivity of extremes", VTE-strong), GTC would follow by leaf induction* (strip `ℓ`, label
`T′` by VTE with parent at 0, re-attach `ℓ` at `m`; L1).

**But VTE-strong is false.** Auxiliary check C (all 47 free trees on ≤ 9 vertices) found 8 counterexample
trees with vertices that admit **no** graceful labeling at label 0 **or** label `m` (check on both
extremes run separately):

| `n` | shape (degree sequence) | vertices blocked from both extremes |
|---|---|---|
| 6 | (3,2,2,1,1,1) — spider S(3,1,1) | the deg-2 vertex mid-leg |
| 7 | (3,3,2,1,1,1,1) | one leaf |
| 8 | (5,2,2,1,1,1,1,1); (4,3,2,1,1,1,1,1); (3,3,2,2,1,1,1,1) | deg-2 vertex; two leaves |
| 9 | (3,3,2,2,2,1,1,1,1); (5,3,2,1,1,1,1,1,1); (4,3,2,2,1,1,1,1,1) | one leaf each |

Note the first counterexample is a **spider with one branching vertex** — even one branch point defeats
prescribed-extreme placement. Any proof strategy that passes through "prescribe an arbitrary vertex at
an extreme" is refuted at `n = 6`; this kills not only L4 but the whole family of would-be inductions
that anchor the extension vertex freely.

**L4′ (the corrected sufficient statement — open).** Replace VTE by **Extendable-Leaf (EL): every tree
with `m ≥ 1` has at least one extendable leaf.** EL implies GTC by the same induction (choose the
extendable leaf each time; EL is quantified over all trees so it iterates). Auxiliary check B2: **EL
holds for all 94 free trees with ≤ 9 vertices** (0 failures). EL is not refuted at small size — but see
L5 for why EL-respecting induction still cannot be carried.

**L5 (Slack Accounting — proved).** *Fix the target slack `σ = M − m` and consider the bottom-up
construction of a slack-σ labeling with `S = {1,…,m}` along a rooted build-up order (each new vertex is
a leaf attached to an already-labeled parent).*

*(a) Dynamic feasibility guard (proved; generalizes the static degree guard
`deg(v) ≤ |{d ∈ S : d ≤ max(a, M−a)}|` for `f(v) = a`). At the step attaching a leaf to a parent whose
current label is `β`, the leaf's label must be one of the ≤ `2(m−i+1)` values `β ± d`, `d` ranging over
the not-yet-used differences. If all remaining differences exceed `max(β, M−β)`, the step is blocked —
and the instance is genuinely infeasible, since a vertex at `β` can only have neighbors at distances
`≤ max(β, M−β)`. The guard does **not** explain the L4 counterexamples (there `max(0, m) = m` admits all
differences), so the L4 failures are structural, not counting artifacts.*

*(b) Commitment accounting (proved). To *guarantee* a step of the construction from an induction
hypothesis, the hypothesis must control the parent's label (a prescription) and keep the leaf's future
label available (a reservation). Each level of the induction thus adds up to two committed labels —
one prescription, one reservation — against a total budget of `M+1` distinct labels. After `i` levels
the commitment count is `≥ i + (i − 1) + O(1)`, so a guarantee-carrying induction can only close when
`2m − O(1) ≤ M + 1`, i.e. **`M ≥ 2m − O(1)` (slack σ ≥ m − O(1))**. At the graceful target `M = m` the
budget is `m+1` and the shortfall is `m − O(1)`: the zero-slack fixed point is unreachable by any
avoidance/prescription-carrying induction. This is the formal content of "removing a leaf destroys
label availability": each leaf extension spends one free label and one unit of control, and graceful
labelings have no free labels to spend.* ∎

**L6 (Parity Invariant — proved; machine-confirmed on every graceful labeling of every tree ≤ 9
vertices, 0 violations).** *For any slack-σ labeling with difference set `S`:
`Σ_{d∈S} d ≡ Σ_v deg(v)·f(v) (mod 2)`.*

*Proof.* `|f(u) − f(v)| ≡ f(u) + f(v) (mod 2)`; sum over edges, noting `Σ_{edges} (f(u)+f(v)) =
Σ_v deg(v) f(v)`, and compare with `Σ_{d=1}^{m} d = m(m+1)/2` in the graceful case. ∎

Any flexibility or descent lemma must respect L6; it is the only universal invariant I could derive
(beyond the static guard in L5a).

**L7 (CPC ≡ GTC — proved, both directions).** *A tree `T` with `m` edges is graceful **iff** it admits a
compatible strip chain (CPC).*

*Proof.* (⇒) Restrict a graceful labeling `f` of `T` along any strip order: `f_i := f|_{V(T_i)}` is
`i`-punctured with `C_i` = the edge labels of the stripped edges, and compatibility holds by
construction. (⇐) A CPC's final stage `T_0 = T` is 0-punctured with `C_0 = ∅`, i.e. graceful. ∎

So the conjecture is **exactly** the statement that punctures can be propagated coherently down a full
strip chain. The L4 counterexample tree at `n = 7` makes the failure visible: its blocked leaf `ℓ` would
need `T − ℓ` labeled punctured-at-`c` with the parent at `c` for some `c` — and the required punctured
configurations fail one level down, on the `n = 6` spider, which itself fails the analogous demand at
its deg-2 mid-leg vertex. **VTE-failure is the shadow of a non-propagating puncture chain.**

---

## 3. Exactly where the chain breaks

The chain L1 → L2/L3 → L4′/L5 → L7 locates the break precisely:

1. **Naive Rosa induction (break #1, formalized by L1).** Leaf deletion does not preserve the label
   domain. The extension from a graceful `T′` is possible only from parent-label 0 (L1′), an event with
   no lower-bound guarantee; empirically its density among graceful labelings of `T′` is often 0 for
   given `(T, ℓ)` (aux check B: 6 of 409 pairs have none), though every small tree has *some*
   extendable leaf (B2).

2. **Composition route (break #2, formalized by L2 + L3).** Every "glue two labeled pieces" strategy
   dies twice: affine maps preserve difference sets (L2), so pieces' edge-label sets collide; and the
   vertex budget forces interleaving (L3), so intact sub-labelings cannot occur in any composite. What
   remains is prescribing complementary difference subsets for both pieces — a Skolem-type pairing
   problem for which the only known technology (Skolem/hooked-Skolem sequences and their caterpillar
   deployments) solves **one-dimensional** constraint systems (paths, stars, caterpillars: constraint
   structure = a matching). Each branching vertex couples the pairing constraints across legs; no
   Skolem-type theorem is known even for two independent branch points. Consistently, the literature's
   graceful families are exactly the bounded-branching / bounded-diameter / symmetric ones *[unverified
   citations]*, and aux check E shows slack-1 flexibility already holds at 3 branch points while
   prescribed-extremal placement fails at **1** branch point.

3. **Strengthened-induction route (break #3, formalized by L4 + L5).** The natural strengthening that
   would power the induction — prescribed-extreme placement (VTE-strong) — is **false at n = 6** (L4).
   The corrected hypothesis EL survives small-size testing, but L5(b) shows that any induction capable
   of *guaranteeing* the extension steps needs slack `Θ(m)`: graceful labelings are the zero-slack fixed
   point, and each leaf step spends exactly the resource (one free label, one unit of parent control)
   that the tight case does not have. Empirically the one-step relaxation is indeed easier: **slack-1
   flexibility with any prescribed vertex at 0 holds for all 94 trees ≤ 9 vertices and all vertices**
   (aux check D), including all 8 trees where the slack-0 version fails. The gap `σ = 1 → σ = 0` is
   already nontrivial — descent, not construction, is the open half.

4. **Why existing methods cannot pass these points.** The three known proof technologies map exactly
   onto the three breaks: (i) explicit zero-slack constructions (Skolem pairings) work when the
   constraint system is a 1-dimensional matching — they do not handle coupled multi-leg constraints
   (break #2/#3); (ii) α-composition-style shifts require all edges to cross a threshold, which L3
   shows cannot survive the join budget; (iii) exhaustive/heuristic search confirms small cases but
   provides no invariant to induct on — L6 (parity) and the L5(a) guard are the only universal
   invariants I could derive, and both are satisfiable in all small counterexamples, i.e. **no known
   invariant separates the L4 counterexample trees from gracefully-prescribable ones.** The obstruction
   is not a missing trick inside one route: all three standard routes terminate at the same wall —
   zero-slack coherence of puncture propagation (L7).

---

## 4. The minimal new lemma that would unblock

By L7 the exact target is coherent puncture propagation. The minimal lemmas, in increasing order of
strength, each of which would unblock the corresponding route:

**(M1) Puncture-Descent for one branch point beyond spiders (testbed: "double-spiders" — trees with
exactly two vertices of degree ≥ 3).** Prove: every double-spider with `m` edges admits, for every `c`
in a parity-respecting (L6) subset of `{1,…,m}`, a 1-punctured labeling into `{0,…,m}` with difference
set `{1,…,m} ∖ {c}` and a **prescribed** vertex of degree ≥ 3 at label `c`. This is the smallest class
where the Skolem matching technology must couple two constraint centers; a proof technique for M1 that
does not special-case the two branch points would be the first genuine advance past caterpillar-class
methods. (Spiders themselves are known graceful *[unverified]* yet already fail prescribed-extremal
placement — so M1's content is puncture *control*, not existence.)

**(M2) Slack-1 ⇒ slack-0 descent (one-step).** For every tree `T` with `m` edges and every vertex `v`
satisfying the L5(a) guard, either (a) exhibit a slack-1 labeling (exists for all small `T, v`; aux D)
together with a **local exchange** that fills the unused label and the missing difference `m+1` without
disturbing more than `O(1)` vertex labels, or (b) show a slack-1 instance where no bounded exchange
exists — which would locate a new obstruction class. Note (aux D vs. L4) that slack-1 flexibility is
*universally* true at small size while its slack-0 shadow is false: the descent lemma is strictly
stronger than what small-scale evidence can confirm, and is exactly the missing half of L5.

**(M3) The exact unblocking lemma (equivalent to GTC by L7, stated for the record).** Every tree admits
a compatible strip chain in which each `c_i` is chosen adaptively subject only to L6 and the L5(a)
guard. Any proof of M3 proves Ringel–Kotzig; conversely GTC gives M3 (L7). The value of the statement is
that it reduces the conjecture to a finite propagation property with two checkable side conditions,
which is the form most likely to admit a computer-assisted invariant argument (e.g., a strategy-stealing
or potential argument over the multiset of available `(parent label, remaining differences)` states).

**Recommendation.** Attack M1. It is formal, small-case-verifiable, sits exactly on the empirical
frontier (aux E), and any technique that survives two coupled branch points is a candidate to iterate.

---

## 5. Verdict: **OBSTRUCTION-IDENTIFIED**

Justification:

- **Not ROUTE-LIVE.** All three classical routes are formally blocked, and the blocks are proved, not
  conjectured: affine rigidity + budget pigeonhole kill composition (L2, L3); the strengthening that
  would power leaf-induction is *refuted* at `n = 6` (L4, machine-checked); guarantee-carrying
  induction needs slack `Θ(m)` while the target has slack 0 (L5). I cannot name a technique that
  currently produces coherent puncture chains (L7) past one branching vertex, so no route is live today.
- **Not DEAD-END.** The obstruction is precisely located and *measurable*: the failure of
  prescribed-extremal placement is a decidable small-scale phenomenon with 8 recorded counterexamples;
  the surviving relaxation (slack-1 flexibility) is empirically universal and separated from the target
  by exactly one descent step (M2); and the CPC reformulation (L7) converts Ringel–Kotzig into a
  propagation property with checkable side conditions (L6 parity, L5(a) guard) — a form to which
  difference-triangle-set / Skolem-design techniques, which have never been tried on coupled
  multi-branch constraint systems, could plausibly be extended (M1).
- The deliverable's requested diagnosis is confirmed and sharpened: naive induction breaks not merely
  because "removing a leaf destroys label availability", but because (i) the extension condition is a
  two-point constraint `{0, m}` (L1), (ii) every composition is budget-blocked (L3), (iii) the natural
  induction-strengthening is false (L4), and (iv) each extension step spends one unit of an
  incompressible resource (L5). The minimal separating object between caterpillar-class and general
  trees is puncture-chain coherence past one branch point (M1).

---

## Appendix: auxiliary computations (boundary confirmation only)

`aux_small_checks.py`, output in `aux_results.txt`. All free trees with ≤ 9 vertices (94 trees, `m ≤ 8`).

- **[A]** Parity invariant L6: 0 violations across all graceful labelings of all 94 trees.
- **[B]** Extension-rigidity density (L1′): mean fraction of `T′`-graceful labelings with parent at 0
  over all 409 `(tree, leaf)` pairs ≈ 0.22; 6 pairs have no extendable labeling at all.
- **[B2]** EL (L4′): every tree has an extendable leaf — 0 failures.
- **[C]** VTE-strong (L4): **8 counterexample trees**; blocked vertices fail at *both* extremes.
- **[D]** Slack-1 flexibility (M2 premise): 0 failures — all trees, all vertices, diffs `{1..m}` into
  `{0..m+1}` with prescribed vertex at 0 (e.g. the `n = 7` counterexample tree has 78 such labelings at
  its blocked vertex, vs. 0 graceful ones).
- **[E]** Stratified by branching count: slack-1 holds in every class (including 6 trees with 3 branch
  vertices); prescribed-extremal fails already in the 1-branch class.
