# Discovery loop

## 1. Reframing

A target problem is rewritten at multiple levels of abstraction. The system explicitly requests domain-light descriptions to reduce the probability of merely retrieving neighboring literature.

Example for the Riemann hypothesis:

- topical: zeros of the zeta function lie on the critical line,
- structural: global zero-location rigidity from hidden coefficient/arithmetic structure,
- functional: local or coefficient-level constraints must force a global analytic geometry,
- failure-aware: avoid reformulations that assume real-rootedness or equivalent positivity.

## 2. Structural retrieval

For each reframing, retrieval runs in two channels:

1. **Analogy retrieval** maximizes mechanism/structure similarity while rewarding domain distance. Historical breakthrough nodes and structurally indexed research claims can become mutation sources.
2. **Research-memory retrieval** favors relevant prior work, same-domain context, and matching failure modes. Claims and evidence from prior sessions are attached to the reasoning payload so known obstructions and negative results remain visible.

Evidence is not treated as a transferable mechanism by default. It can support, weaken, contradict, or falsify claims in memory, while direct analogical mutation is restricted to historical nodes and claims.

A nearby number-theory paper is useful for prior art, but it is not necessarily the primary discovery candidate. A theorem in statistical mechanics, operator theory, or geometry may rank higher in the analogy channel if its mechanism matches, while same-problem prior work can still rank highly in the memory channel.

## 3. Analogical mutation

The system should not copy the historical method literally. It decomposes the source breakthrough into:

1. obstacle,
2. enabling structure,
3. transformation,
4. gained rigidity,
5. cost/assumption.

It then mutates one or more of these components for the target problem.

## 4. Adversarial falsification

A separate critic looks for:

- circularity,
- assumptions equivalent to the original problem,
- loss of the theorem's enabling structure,
- non-uniform limit exchanges,
- finite-size artifacts,
- universal representation theorems that make the result vacuous,
- known no-go theorems.

## 5. Proof-obligation extraction

A surviving idea is rewritten as a chain of implications. The engine marks the weakest unknown edge.

The next action is not "prove the whole conjecture". It is "attack the cheapest unknown edge".

## 6. Verification

Future workers can route obligations to:

- literature search,
- Python counterexample search,
- symbolic algebra,
- numerical simulation,
- theorem proving,
- Lean 4 formalization.

A numerical result is never automatically upgraded to a proof.

## 7. Memory update

Both successes and failures are saved. Failure meta-lessons become retrieval penalties in subsequent runs.
