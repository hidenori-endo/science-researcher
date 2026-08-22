"""Value-stream families and clairvoyant benchmarks."""

import math
import random

T = 2000
N_IID_SEEDS = 30


# ---------- IID families: gen(seed) -> list of T values ----------

def _uniform01(seed):
    rng = random.Random(seed)
    return [rng.random() for _ in range(T)]


def _powlaw(seed, vmin=0.01, alpha=1.5):
    # density proportional to v^-alpha on [vmin, 1]; inverse-CDF sampling.
    b = vmin ** (1 - alpha)
    rng = random.Random(seed)

    def sample():
        u = rng.random()
        return (b + u * (1 - b)) ** (1 / (1 - alpha))

    return [sample() for _ in range(T)]


def _bimodal(seed):
    rng = random.Random(seed)
    vals = []
    for _ in range(T):
        if rng.random() < 0.5:
            vals.append(rng.uniform(0.0, 0.15))
        else:
            vals.append(rng.uniform(0.6, 1.0))
    return vals


def _lognormal(seed, mu=-2.0, sigma=0.75):
    # Box-Muller; clipped to (0,1] (clipping is a declared caveat).
    rng = random.Random(seed)
    vals = []
    while len(vals) < T:
        u1, u2 = rng.random(), rng.random()
        if u1 <= 0:
            continue
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        vals.append(min(1.0, max(1e-9, math.exp(mu + sigma * z))))
    return vals


# ---------- Clairvoyant optimal fixed price (knows distribution) ----------

def best_fixed_iid(streams):
    """Monte Carlo optimum over p in (0,1] given pooled samples (200k draws).
    Returns (best_p, per-round optimal revenue)."""
    pool = []
    for s in streams[:100]:  # each stream has T=2000 -> up to 200k draws
        pool.extend(s)
    pool.sort()
    n = len(pool)
    import bisect
    best_p, best_rev = 0.0, -1.0
    for i in range(1, 10001):
        p = i / 10000
        k = n - bisect.bisect_left(pool, p)
        rev = p * k / n
        if rev > best_rev:
            best_p, best_rev = p, rev
    return best_p, best_rev


# ---------- Permutation families ----------

def perm_multisets():
    return {
        "perm-spike-zero": [1.0] + [0.0] * (T - 1),
        "perm-two-level": [1.0] * (T // 2) + [0.4] * (T - T // 2),
        "perm-wide-tail": [1.0] * 3 + [0.7] * 27 + [0.02] * (T - 30),
    }


def perm_instances():
    """name -> list of (instance_label, ordered_values)."""
    out = {}
    for name, ms in perm_multisets().items():
        insts = [("asc", sorted(ms)), ("desc", sorted(ms, reverse=True))]
        for k in range(10):
            shuf = list(ms)
            random.Random(1000 + k).shuffle(shuf)
            insts.append((f"rand{k}", shuf))
        out[name] = insts
    return out


def best_fixed_multiset(multiset):
    """Exact clairvoyant fixed price over a known multiset."""
    distinct = sorted(set(multiset), reverse=True)
    best_rev = 0.0
    best_p = 0.0
    for v in distinct:
        if v <= 0:
            continue
        cnt = sum(1 for x in multiset if x >= v)
        rev = v * cnt
        if rev > best_rev:
            best_rev, best_p = rev, v
    return best_p, best_rev


# ---------- Myerson note ----------
# For a single IID buyer the revenue-maximizing mechanism IS a posted price at
# the monopoly reserve r maximizing r*(1-F(r)); that equals the clairvoyant
# best fixed price above. So "Myerson optimal" == "clairvoyant fixed" here and
# is reported as the same number (see RESULTS.md).
