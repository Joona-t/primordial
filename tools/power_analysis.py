"""Statistical power analysis for Primordial Computing v2.0 experiments.

Computes sample sizes needed to detect natural violation rates at various
confidence levels. Uses exact binomial (Clopper-Pearson) intervals.

This tool directly addresses the v1.0 gap: 0/30 natural violations gave
a CP upper bound of 11.6%. How many runs do we need to tighten this?
"""

from scipy import stats
import json


def clopper_pearson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """Upper bound of Clopper-Pearson confidence interval.

    Args:
        k: Number of successes (violations detected)
        n: Number of trials (runs)
        alpha: Significance level (default 0.05 for 95% CI)

    Returns:
        Upper bound of the confidence interval
    """
    if k == n:
        return 1.0
    return stats.beta.ppf(1 - alpha / 2, k + 1, n - k)


def clopper_pearson_lower(k: int, n: int, alpha: float = 0.05) -> float:
    """Lower bound of Clopper-Pearson confidence interval."""
    if k == 0:
        return 0.0
    return stats.beta.ppf(alpha / 2, k, n - k + 1)


def sample_size_for_upper_bound(target_upper: float, k: int = 0,
                                 alpha: float = 0.05) -> int:
    """Find minimum sample size where CP upper bound <= target.

    Given k observed violations, how many total runs needed so the
    95% upper bound on the true rate is at most target_upper?

    Args:
        target_upper: Maximum acceptable CP upper bound (e.g., 0.02 for 2%)
        k: Number of violations observed (default 0)
        alpha: Significance level

    Returns:
        Minimum sample size n
    """
    for n in range(max(k + 1, 10), 10000):
        ub = clopper_pearson_upper(k, n, alpha)
        if ub <= target_upper:
            return n
    return -1  # not found within range


def power_to_detect(true_rate: float, n: int, alpha: float = 0.05) -> float:
    """Power to detect a non-zero violation rate.

    Probability of observing at least 1 violation in n runs
    if the true rate is true_rate.

    Args:
        true_rate: Hypothesized true violation rate
        n: Number of runs
        alpha: Not used directly (power = 1 - P(k=0))

    Returns:
        Statistical power (probability of detecting >= 1 violation)
    """
    # P(detect) = 1 - P(k=0) = 1 - (1 - true_rate)^n
    return 1.0 - (1.0 - true_rate) ** n


def sample_size_for_power(true_rate: float, target_power: float = 0.95) -> int:
    """Minimum sample size to achieve target power.

    How many runs needed so P(detect >= 1 violation) >= target_power?

    Args:
        true_rate: Hypothesized true violation rate
        target_power: Desired power (default 0.95)

    Returns:
        Minimum sample size
    """
    import math
    # n >= log(1 - power) / log(1 - rate)
    if true_rate <= 0 or true_rate >= 1:
        return -1
    n = math.ceil(math.log(1 - target_power) / math.log(1 - true_rate))
    return max(n, 1)


def generate_power_table() -> dict:
    """Generate comprehensive power analysis table for the study.

    Returns dict with:
    - upper_bound_table: sample sizes to achieve various CP upper bounds (if 0 violations)
    - power_table: power to detect various true rates at various sample sizes
    - sample_size_table: sample sizes needed for various rate/power combos
    """

    # Table 1: If we observe 0 violations, what CP upper bound do we get?
    upper_bound_table = []
    for n in [30, 50, 75, 100, 150, 200, 300, 500, 750, 1000]:
        ub = clopper_pearson_upper(0, n)
        upper_bound_table.append({
            "n": n,
            "k": 0,
            "cp_upper_95": round(ub, 4),
            "cp_upper_pct": f"{ub * 100:.1f}%"
        })

    # Table 2: Sample size needed to achieve target CP upper bound (with 0 violations)
    target_bounds = [0.10, 0.05, 0.03, 0.02, 0.01, 0.005]
    bound_requirements = []
    for target in target_bounds:
        n = sample_size_for_upper_bound(target)
        bound_requirements.append({
            "target_upper_pct": f"{target * 100:.1f}%",
            "required_n": n,
            "actual_upper": round(clopper_pearson_upper(0, n), 4) if n > 0 else None
        })

    # Table 3: Power to detect true rates at various sample sizes
    true_rates = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20]
    sample_sizes = [30, 50, 100, 200, 300, 500]
    power_table = []
    for rate in true_rates:
        row = {"true_rate_pct": f"{rate * 100:.0f}%"}
        for n in sample_sizes:
            p = power_to_detect(rate, n)
            row[f"n={n}"] = f"{p:.3f}"
        power_table.append(row)

    # Table 4: Sample size needed for target power at various true rates
    target_powers = [0.80, 0.90, 0.95, 0.99]
    size_table = []
    for rate in true_rates:
        row = {"true_rate_pct": f"{rate * 100:.0f}%"}
        for power in target_powers:
            n = sample_size_for_power(rate, power)
            row[f"power={power}"] = n
        size_table.append(row)

    return {
        "upper_bound_if_zero": upper_bound_table,
        "sample_size_for_bound": bound_requirements,
        "power_matrix": power_table,
        "sample_size_for_power": size_table,
        "v1_baseline": {
            "n": 30,
            "k": 0,
            "cp_upper_95": round(clopper_pearson_upper(0, 30), 4),
            "note": "v1.0 result: 0/30 natural violations"
        },
        "v2_target": {
            "n": 200,
            "k_expected": 0,
            "cp_upper_95_if_zero": round(clopper_pearson_upper(0, 200), 4),
            "power_at_5pct_rate": round(power_to_detect(0.05, 200), 4),
            "power_at_2pct_rate": round(power_to_detect(0.02, 200), 4),
            "note": "v2.0 target: 200 runs, tighten bound to ~1.5%"
        }
    }


if __name__ == "__main__":
    results = generate_power_table()

    print("=" * 70)
    print("PRIMORDIAL v2.0 — Statistical Power Analysis")
    print("=" * 70)

    print("\n--- v1.0 Baseline ---")
    v1 = results["v1_baseline"]
    print(f"  {v1['n']} runs, {v1['k']} violations → CP upper bound: {v1['cp_upper_95']:.1%}")

    print("\n--- v2.0 Target ---")
    v2 = results["v2_target"]
    print(f"  {v2['n']} runs (if 0 violations) → CP upper bound: {v2['cp_upper_95_if_zero']:.1%}")
    print(f"  Power to detect 5% true rate: {v2['power_at_5pct_rate']:.1%}")
    print(f"  Power to detect 2% true rate: {v2['power_at_2pct_rate']:.1%}")

    print("\n--- Table 1: CP Upper Bound if 0 Violations ---")
    print(f"  {'N':>6}  {'CP Upper 95%':>14}")
    for row in results["upper_bound_if_zero"]:
        print(f"  {row['n']:>6}  {row['cp_upper_pct']:>14}")

    print("\n--- Table 2: Required N for Target CP Upper Bound ---")
    print(f"  {'Target':>10}  {'Required N':>12}  {'Actual UB':>10}")
    for row in results["sample_size_for_bound"]:
        actual = f"{row['actual_upper']:.4f}" if row["actual_upper"] else "N/A"
        print(f"  {row['target_upper_pct']:>10}  {row['required_n']:>12}  {actual:>10}")

    print("\n--- Table 3: Power to Detect (>= 1 violation) ---")
    header = f"  {'Rate':>6}"
    for n in [30, 50, 100, 200, 300, 500]:
        header += f"  {'n=' + str(n):>8}"
    print(header)
    for row in results["power_matrix"]:
        line = f"  {row['true_rate_pct']:>6}"
        for n in [30, 50, 100, 200, 300, 500]:
            line += f"  {row[f'n={n}']:>8}"
        print(line)

    print("\n--- Table 4: Sample Size for Target Power ---")
    header = f"  {'Rate':>6}"
    for p in [0.80, 0.90, 0.95, 0.99]:
        header += f"  {'p=' + str(p):>8}"
    print(header)
    for row in results["sample_size_for_power"]:
        line = f"  {row['true_rate_pct']:>6}"
        for p in [0.80, 0.90, 0.95, 0.99]:
            line += f"  {row[f'power={p}']:>8}"
        print(line)

    # Save JSON
    output_path = "power_analysis_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
