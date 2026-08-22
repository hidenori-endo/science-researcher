# combo:noether-loop-invariants — STAGE-2 validation on real SV-COMP benchmarks

Stage-1 (`experiments/noether-loop-invariants/`, commit `49f54b5^`) passed cheap
falsification on 30 hand-written loops: 76.7% extended / 50.0% strict coverage.
Stage-2 asks the two questions that actually matter:

1. does the symmetry-derived approach hold up on **real verification
   benchmarks**, and
2. does it **add anything over a classic template baseline**?

## Pre-registered criteria

**Written and committed before the full-corpus numbers below were produced.**
(A 30-loop smoke run was done earlier solely to validate the pipeline plumbing;
its numbers are not stage-2 evidence and were not used to tune anything.)

Verdict rule, exactly as registered in the task definition:

- **UPGRADE** iff *both*:
  - strict-symmetry-only coverage is within **15 points** of baseline coverage,
    AND
  - at least **5 corpus loops** get nonlinear (degree >= 2) invariants that the
    linear baseline misses;
- **DOWNGRADE** iff *either*:
  - baseline coverage exceeds symmetry-only coverage by **more than 30 points**,
    OR
  - nonlinear wins < **5**;
- otherwise **INCONCLUSIVE**.

The DOWNGRADE condition is checked first; if it holds the verdict is DOWNGRADE
even if the UPGRADE condition would also be satisfied (the UPGRADE condition
requires wins >= 5, so both can only co-hold when baseline leads by >30 points
while symmetry still finds >=5 nonlinear wins — such an outcome is recorded as
DOWNGRADE per this precedence).

### Metric definitions (also pre-registered)

*Corpus*: integer while-loops extracted by the tolerant C parser (`parse_c.py`)
from a sparse checkout of sosy-lab/sv-benchmarks (loop-rich directories +
bitvector dirs), under the parse filter documented in that file. Both methods
run on byte-identical `CLoop` transition relations.

*Verification-grade coverage of a method* = fraction of evaluated loops on which
the method outputs at least one **validated inductive invariant**: a candidate
`q` with exact rational coefficients such that on EVERY branch of the loop
`q(f(x)) == q(x)` (conserved) or `q(f(x)) == kappa*q(x)` for rational kappa with
`q(init) == 0` (covariant zero level set) — checked as symbolic polynomial
identities over Q — plus a numeric sanity pass over simulated reachable states,
and nontriviality (touches >=2 variables or has degree >=2, and touches at least
one mutated variable). This is the real-corpus analogue of stage-1's
verification-grade test: real SV-COMP files carry no uniformly extractable
polynomial post-condition target, so entailment-of-target cannot be scored;
inductive validity + nontriviality is what "verification-grade" reduces to here.

*Method variants*:

- **SYM (strict)**: stage-1 finite-automorphism eigenforms only — homogeneous
  linear transforms T: x_i -> c*x_sigma(i) detected as exact automorphisms of
  the transition relation, eigenforms extracted via exact cycle-decomposition
  eigenvalues on the degree-<=2 monomial basis (this replaces stage-1's fixed
  small-rational lambda probe with a provably complete per-image computation).
  NO translation duality.
- **SYM (extended)**: strict + translation duality (reported for continuity
  with stage 1; stage 1 itself noted translation duality degenerates to known
  linear techniques).
- **BASELINE**: classic template-based linear invariant generation — affine
  templates q = l.x + c solved EXACTLY: one homogeneous linear system
  (l.(A_b - I) = 0 and l.b_b = 0 for every branch) over Q via Gaussian
  elimination. This is precisely what stage-1's translation duality reduces to.
- **BASELINE+eigen** (transparency variant): additionally solves linear
  multiplicative templates l.A_b = lambda*l, l.b_b = 0 over a small-rational
  lambda probe list. Reported so the "nonlinear wins" claim can be checked
  against the stronger linear competitor too. The headline baseline for the
  pre-registered comparison is BASELINE+eigen (stronger baseline => more
  conservative UPGRADE assessment); both are tabulated.

*Nonlinear win*: a loop where SYM(strict) validates a degree>=2 invariant and
BASELINE(+eigen) validates nothing at all on that loop.

*Symmetry-search caps (fixed before the run)*: coefficient sets shrink with
dimension (n<=2: {+-1,+-2,+-3,+-4,+-9}; 3<=n<=4: {+-1,+-2}; n=5: {+-1}); no
finite-automorphism search at n>=6; at most 64 detected images get eigenform
extraction per loop. Loops hitting these caps are counted honestly.

## Corpus

Sparse clone of https://github.com/sosy-lab/sv-benchmarks (depth 1,
blob:none), sparse-checkout of: loop-invariants, loop-invgen, loop-crafted,
loops, loop-simple, loop-zilu, loop-lit, loop-new, loops-crafted-1,
loop-acceleration, loop-industry-pattern, bitvector-loops,
bitvector-regression, bitvector, array-crafted, array-examples (.c and .i).

Parser fragment (pre-registered, identical filters for both methods):
signed int-family scalars only; unsigned/bitwise/div-mod/arrays/pointers/
floats rejected; deterministic polynomial updates; if/else expanded into
<=16 guarded paths; `while(nondet())` allowed; unknown initial values become
parameters pinned to 0 for the numeric sanity pass only. Soundness note:
validation uses exact identities on every branch, so guards do not affect
soundness, only the sanity simulation. Structural duplicates removed.

## Results (full corpus)

Run: `python3 run.py --out results.json` (deterministic; exact rational
arithmetic throughout; wall clock ~2 min on 132 loops, well under the 45-min
cap).

### Corpus yield (honest parse statistics)

| stage | count |
|---|---|
| files scanned (.c + .i) | 798 |
| functions parsed | 2108 |
| while/for loops reached by the extractor | 1011 |
| extraction attempts succeeding | 273 |
| structural duplicates removed (incl. .c/.i twins of the same benchmark) | 141 |
| **unique loops evaluated** | **132** |

Why only 132 of 1011: this is the pre-registered fragment doing its job, not a
parser bug budget. Dominant honest rejections over whole files or individual
loops: unsigned variables / bitwise arithmetic (~350 events; bitvector
semantics are out of scope for exact rational arithmetic), array accesses
(~165), division/modulo in guards or updates (~38), goto/switch/do control
flow (~70), nondeterministic assignments inside loop bodies (15), nested loops
(37), plus GNU-extension syntax the tolerant parser resyncs past. 101/132
loops contain at least one symbolic-parameter variable (nondet inputs pinned
to stand-in values); size profile: nvars 1:11, 2:62, 3:42, 4:15, 5:2;
branches 1:101, 2:24, 3:2, 4:3, 6:2.

### Method table (132 loops)

| method | hits | coverage |
|---|---|---|
| SYM strict (finite-automorphism eigenforms only) | 44 | **33.3%** |
| SYM extended (strict + translation duality) | 69 | **52.3%** |
| BASELINE conserved affine templates | 64 | **48.5%** |
| BASELINE + linear eigen templates | 64 (+0) | **48.5%** |
| overlap both (sym strict & baseline) | 37 | 28.0% |
| symmetry-strict ONLY | 7 | 5.3% |
| baseline ONLY | 27 | 20.5% |

Runtime: symmetry engine 59 s (strict) + 58 s (extended half), baseline 4.6 s
— the symmetry search is ~25x slower.

### Pre-registered verdict computation

- coverage gap, baseline(+eigen) minus SYM(strict): 48.48% - 33.33% =
  **15.15 points** -> NOT within the 15-point UPGRADE window;
- nonlinear wins (pre-registered definition, degree >= 2): **7** (>= 5);
- DOWNGRADE conditions: gap > 30 points? no. wins < 5? no.

## Verdict

**INCONCLUSIVE** under the pre-registered criteria: neither the UPGRADE
condition (coverage within 15 points fails at 15.15) nor either DOWNGRADE
condition (gap 15.2 < 30; wins 7 >= 5) holds.

An honest post-hoc stricter reading is recorded below; it does not replace the
pre-registered verdict but materially weakens the case for the hypothesis.

## Failure analysis

1. **The strict-symmetry coverage gap is exactly the translation-duality
   share.** All 27 baseline-only loops are pure constant-step counter loops
   (e.g. `array-examples/standard_two_index_02..09`: `j - 1/2*i == -1/2`):
   pure translations have no nontrivial finite automorphism (T o f = f o T
   forces c = 1), so strict symmetry is blind to them BY DESIGN, while the
   linear baseline solves them by one Gaussian elimination. Adding translation
   duality lifts the symmetry engine to 52.3% — but stage 1 itself already
   conceded that translation duality degenerates to the same linear algebra
   the baseline performs. The honest reading: **the symmetry-specific content
   of the pipeline covers a minority of real loops (33%), and the workhorse is
   again the part that is not symmetry at all.**

2. **The 7 "nonlinear wins" decompose into 1 genuine + 6 artifacts.**
   Pre-registered definition (degree >= 2 as a polynomial) gives 7 loops where
   SYM validates an invariant the baseline misses:
   - `loop-zilu/benchmark01_conjunctive` (`x=x+y; y=x` from (1,1)):
     **genuinely quadratic** — `y^2 - x*y`, `y^2 - x^2` conserved at level 0
     via covariance, found as eigenforms of the detected Fibonacci-scaling
     structure. The linear baseline finds nothing here. This is the single
     clean stage-2 confirmation of the stage-1 `square-track` mechanism.
   - `loops/sum01-2`, `loops/sum04-2`: `sn - i*a == 0` where `a` is the macro
     `#define a (2)`: after preprocessor stripping `a` becomes a symbolic
     parameter, so the invariant is degree-2 as a polynomial but **linear in
     the mutated variables** (sn = 2i). Artifact.
   - `loops/trex01-1`: `k*z == 0`, k a nondet-fixed parameter. Same artifact.
   - `loops-crafted-1/theatreSquare` (3 sequential loops): `b - a*i`,
     `l - a*j`, `y - j*x` — `a` is a function parameter and `j` a
     frozen-by-earlier-loop value; all three are linear in the mutated
     variables with a symbolic-constant coefficient. Artifacts.
   Under the stricter reading "degree >= 2 in the loop's MUTATED variables",
   nonlinear wins = **1 < 5**, which would fire the DOWNGRADE condition. This
   reading is post-hoc, so the official verdict remains INCONCLUSIVE — but a
   stage-3 design should pre-register the stricter definition.

3. **What symmetry genuinely adds over the linear baseline** is narrow but
   real: (a) one loop with genuinely quadratic conserved quantities;
   (b) 5 loops with **parametric-coefficient invariants** (`sn - i*a`,
   `b - a*i`, `k*z`, `y - j*x`) which the constant-coefficient linear template
   baseline cannot express at all — degree-2 monomials act as a proxy for
   coefficients that are unknown-but-fixed inputs. That mechanism is a true
   capability delta, just rarer on this corpus than the 15-point window
   demanded.

4. **Linear eigen templates added nothing** (+0 loops): the small-rational
   lambda probe never fired where conserved templates failed, consistent with
   stage 1's finding that scaling-symmetry loops are rare in real corpora
   compared with hand-written suites.

5. **Structural blind spots persist from stage 1**: quadratic accumulators
   (`gauss-sum`-shaped loops) still have no point symmetry to exploit; the
   corpus contains several (`loop-lit/*`, `loop-invgen/half_*` are caught by
   the baseline instead). Inequality/disjunctive post-conditions remain outside
   the equality fragment entirely.

## Recommendation

Keep the stage-1 recommendation ("partially supported on the counter/scaling
family; do not adopt as a general invariant-inference principle") and add:
the symmetry mechanism's only verified real-corpus additions are
parametric-coefficient and quadratic eigenforms — a niche worth at most a
seed-generator role inside a larger template solver, not a standalone method.
Stage-3 (if any): pre-register "nonlinear = degree >= 2 in mutated variables
only", and hybridize with the cohomological solver as suggested at the end of
stage 1; without closing the quadratic-accumulator gap the approach cannot
beat a plain linear template solver on SV-COMP-like corpora.
