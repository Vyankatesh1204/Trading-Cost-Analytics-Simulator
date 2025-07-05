# impact_model.py

import numpy as np

class AlmgrenChrissModel:
    def __init__(self, X, N, sigma, eta, gamma, lambd, T):
        """
        X: Total shares to trade
        N: Number of time steps
        sigma: Volatility
        eta: Temporary impact
        gamma: Permanent impact
        lambd: Risk aversion
        T: Total time
        """
        self.X = max(0.01, X)
        self.N = max(1, N)
        self.sigma = max(1e-6, sigma)
        self.eta = max(1e-6, eta)
        self.gamma = max(0.0, gamma)
        self.lambd = max(1e-10, lambd)
        self.T = max(1e-3, T)
        self.dt = self.T / self.N

    def optimal_trajectory(self):
        """
        Returns the optimal execution schedule (x_0, x_1, ..., x_N)
        """
        kappa = np.sqrt(self.lambd * self.sigma**2 / self.eta)
        times = np.arange(self.N + 1) * self.dt
        sinh_kappa_T = np.sinh(kappa * self.T)

        if sinh_kappa_T == 0 or np.isnan(sinh_kappa_T) or np.isinf(sinh_kappa_T):
            print("⚠️ Unstable sinh(kappa*T) in trajectory. Returning flat schedule.")
            return np.full(self.N + 1, self.X / (self.N + 1))

        x = self.X * (np.sinh(kappa * (self.T - times)) / sinh_kappa_T)
        return x

    def expected_cost(self):
        """
        Calculate the expected cost of the optimal strategy
        """
        kappa = np.sqrt(self.lambd * self.sigma**2 / self.eta)
        sinh_kappa_T = np.sinh(kappa * self.T)

        if sinh_kappa_T == 0 or np.isnan(sinh_kappa_T) or np.isinf(sinh_kappa_T):
            print("⚠️ Unstable sinh(kappa*T). Falling back to 0 impact cost.")
            return 0.0

        cost = (
            self.gamma * self.X**2
            + self.eta * self.X**2 * kappa * np.cosh(kappa * self.T) / sinh_kappa_T
        )

        if np.isnan(cost) or np.isinf(cost):
            print("⚠️ Computed expected cost is invalid. Returning 0.")
            return 0.0

        return cost