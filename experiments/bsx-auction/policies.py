"""Sample-free posted-price policies as portfolios over a public price grid.

Model: T rounds, one buyer per round. Policy posts p from a fixed public grid.
Sale iff v >= p; revenue p. Feedback: bandit (sale indicator / own revenue
only). No distributional samples are available to any policy.
"""

import math
import random


def make_grid(n=16, vmax=1.0):
    """Uniform public grid on (0, vmax]."""
    return [vmax * i / n for i in range(1, n + 1)]


class Policy:
    name = "base"

    def __init__(self, grid):
        self.grid = grid
        self.n = len(grid)

    def choose(self, t):
        """Return grid index to post at round t (t is 1-based)."""
        raise NotImplementedError

    def update(self, idx, revenue, sold):
        """Observe outcome of posting grid[idx]."""
        pass


class UniformMix(Policy):
    """Pure portfolio: uniform random price each round."""
    name = "uniform-mix"

    def choose(self, t):
        return random.randrange(self.n)


class Exp3(Policy):
    """EXP3 with importance-weighted rewards over the price grid."""
    name = "exp3"

    def __init__(self, grid, horizon, gamma=None):
        super().__init__(grid)
        ln_n = math.log(self.n)
        self.gamma = gamma if gamma is not None else min(
            1.0, math.sqrt(self.n * ln_n / max(horizon, 1)))
        self.w = [1.0] * self.n
        self.p = [1.0 / self.n] * self.n

    def choose(self, t):
        s = sum(self.w)
        g = self.gamma
        self.p = [(1 - g) * wi / s + g / self.n for wi in self.w]
        r = random.random()
        acc = 0.0
        for i, pi in enumerate(self.p):
            acc += pi
            if r <= acc:
                return i
        return self.n - 1

    def update(self, idx, revenue, sold):
        x = revenue / self.p[idx] if revenue > 0 else 0.0
        self.w[idx] *= math.exp(self.gamma * x / self.n)


class Exp3Anytime(Exp3):
    """EXP3 variant with decreasing gamma_t (unknown horizon / doubling-style)."""
    name = "exp3-anytime"

    def __init__(self, grid, horizon=None):
        super().__init__(grid, horizon=1)
        self._ln_n = math.log(self.n)

    def choose(self, t):
        self.gamma = min(1.0, math.sqrt(self.n * self._ln_n / max(t, 1)))
        return super().choose(t)


class EpsGreedy(Policy):
    """eps = 1/n forced exploration, otherwise empirically best price."""
    name = "eps-greedy"

    def __init__(self, grid):
        super().__init__(grid)
        self.eps = 1.0 / self.n
        self.sum = [0.0] * self.n
        self.cnt = [0] * self.n

    def choose(self, t):
        if random.random() < self.eps:
            return random.randrange(self.n)
        best, best_val = 0, -1.0
        for i in range(self.n):
            m = self.sum[i] / self.cnt[i] if self.cnt[i] else 0.0
            if m > best_val:
                best, best_val = i, m
        return best

    def update(self, idx, revenue, sold):
        self.sum[idx] += revenue
        self.cnt[idx] += 1


class UCB1(Policy):
    """Standard UCB1 over price arms with revenue rewards."""
    name = "ucb1"

    def __init__(self, grid):
        super().__init__(grid)
        self.sum = [0.0] * self.n
        self.cnt = [0] * self.n

    def choose(self, t):
        for i in range(self.n):
            if self.cnt[i] == 0:
                return i
        best, best_val = 0, -1.0
        for i in range(self.n):
            u = self.sum[i] / self.cnt[i] + math.sqrt(2 * math.log(t) / self.cnt[i])
            if u > best_val:
                best, best_val = i, u
        return best

    def update(self, idx, revenue, sold):
        self.sum[idx] += revenue
        self.cnt[idx] += 1


def make_policies(grid, horizon):
    return [
        UniformMix(grid),
        Exp3(grid, horizon),
        Exp3Anytime(grid),
        EpsGreedy(grid),
        UCB1(grid),
    ]
