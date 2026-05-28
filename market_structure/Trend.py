import numpy as np
import pandas as pd
from scipy import stats


class Trend:
    def __init__(self, df: pd.DataFrame):
        required = {"open", "high", "low", "close"}
        if not required.issubset(df.columns):
            missing = required - set(df.columns)
            raise ValueError(f"Missing required columns: {missing}")

        self.df = df.copy().reset_index(drop=True)

        if len(self.df) < 3:
            raise ValueError("Need at least 3 rows")

        self.opens = self.df["open"].to_numpy(dtype=float)
        self.highs = self.df["high"].to_numpy(dtype=float)
        self.lows = self.df["low"].to_numpy(dtype=float)
        self.closes = self.df["close"].to_numpy(dtype=float)

        self.n = len(self.df)
        self.window_range = max(self.highs.max() - self.lows.min(), 1e-9)
        self.total_path = max(np.sum(np.abs(np.diff(self.closes))), 1e-9)
        self.total_bar_range = max(np.sum(self.highs - self.lows), 1e-9)
        self.mean_bar_range = max(np.mean(self.highs - self.lows), 1e-9)

    def efficiency(self) -> float:
        """
        Net displacement relative to total close-to-close travel.
        1 = very directional, 0 = very choppy.
        """
        net = abs(self.closes[-1] - self.closes[0])
        return float(net / self.total_path)

    def net_range_ratio(self) -> float:
        """
        Net displacement relative to the full window range.
        High = directional use of the available range.
        Low = lots of movement but little net progress.
        """
        net = abs(self.closes[-1] - self.closes[0])
        return float(net / self.window_range)

    def overlap(self) -> float:
        """
        Mean fractional overlap between consecutive bars.
        High = congestion / consolidation tendency.
        """
        vals = []
        for i in range(1, self.n):
            curr_range = self.highs[i] - self.lows[i]
            if curr_range <= 1e-9:
                continue

            ov = max(
                0.0,
                min(self.highs[i], self.highs[i - 1]) -
                max(self.lows[i], self.lows[i - 1]),
            )
            vals.append(ov / curr_range)

        return float(np.mean(vals)) if vals else 0.0

    def linearity(self) -> float:
        """
        R^2 of regression through closes.
        High = straighter movement.
        """
        x = np.arange(self.n, dtype=float)
        y = self.closes
        _, _, r_value, _, _ = stats.linregress(x, y)
        return float(r_value ** 2)

    def slope_range_ratio(self) -> float:
        """
        Regression slope scaled by the current window range.
        Relative only to the current sample.
        """
        x = np.arange(self.n, dtype=float)
        slope, _, _, _, _ = stats.linregress(x, self.closes)
        return float(slope * (self.n - 1) / self.window_range)

    def expansion_ratio(self) -> float:
        """
        Full window expansion relative to all intrabar movement.
        High = movement turned into actual expansion.
        Low = churn / back-and-forth.
        """
        return float(self.window_range / self.total_bar_range)

    def directional_agreement(self) -> float:
        """
        Fraction of close-to-close moves aligned with the window's net direction.
        """
        diffs = np.diff(self.closes)
        if len(diffs) == 0:
            return 0.0

        net = self.closes[-1] - self.closes[0]
        if abs(net) <= 1e-9:
            return 0.0

        sign = 1 if net > 0 else -1
        aligned = np.sum(np.sign(diffs) == sign)
        return float(aligned / len(diffs))

    def direction(self) -> str:
        net = self.closes[-1] - self.closes[0]
        if abs(net) / self.window_range < 0.15:
            return "FLAT"
        return "UP" if net > 0 else "DOWN"

    def metrics(self) -> dict:
        return {
            "efficiency": self.efficiency(),
            "net_range_ratio": self.net_range_ratio(),
            "overlap": self.overlap(),
            "linearity": self.linearity(),
            "slope_range_ratio": self.slope_range_ratio(),
            "expansion_ratio": self.expansion_ratio(),
            "directional_agreement": self.directional_agreement(),
            "direction": self.direction(),
        }

    def classify(self) -> str:
        m = self.metrics()

        # You can tune these yourself later
        dir_strength = (
            0.40 * m["efficiency"]
            + 0.25 * m["net_range_ratio"]
            + 0.20 * min(abs(m["slope_range_ratio"]), 1.0)
            + 0.15 * m["directional_agreement"]
        )

        structure = (
            0.60 * m["linearity"]
            + 0.40 * (1.0 - min(m["overlap"], 1.0))
        )

        consolidation = (
            0.45 * min(m["overlap"], 1.0)
            + 0.30 * (1.0 - m["net_range_ratio"])
            + 0.25 * (1.0 - m["expansion_ratio"])
        )

        direction = m["direction"]

        if consolidation > 0.62 and dir_strength < 0.45:
            if direction == "UP":
                return "UP_BIASED_CONSOLIDATION"
            elif direction == "DOWN":
                return "DOWN_BIASED_CONSOLIDATION"
            return "PURE_CONSOLIDATION"

        if dir_strength > 0.60 and structure > 0.55:
            if direction == "UP":
                return "UP_TREND"
            elif direction == "DOWN":
                return "DOWN_TREND"

        if dir_strength > 0.45:
            if direction == "UP":
                return "UP_GRIND"
            elif direction == "DOWN":
                return "DOWN_GRIND"

        if direction == "FLAT":
            return "VOLATILE_CHOP"

        return f"CHOP_WITH_BIAS_{direction}"