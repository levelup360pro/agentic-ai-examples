"""Visualization and analysis helpers for pattern experiments.

Lightweight utilities to compare quality and cost across generation patterns.
Only plotting/data-shaping here; no model logic.
"""

import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Dict

def create_comparison_dataframe(pattern_stats: List[dict]) -> pd.DataFrame:
    """Create a comparison dataframe from pattern statistics.

    Args:
        pattern_stats: List of per-pattern summary dicts with keys like
            'pattern', 'avg_quality', and 'avg_cost'.

    Returns:
        A pandas DataFrame with one row per pattern and numeric columns
        for aggregation/plotting.
    """
    return pd.DataFrame(pattern_stats)

def plot_quality_comparison(df: pd.DataFrame, output_path: str):
    """Save a bar chart of average quality by pattern.

    Args:
        df: Dataframe with at least 'pattern' and 'avg_quality' columns.
        output_path: File path to save the resulting image.
    """
    plt.figure(figsize=(10, 6))
    plt.bar(df['pattern'], df['avg_quality'])
    plt.axhline(y=7.0, color='r', linestyle='--', label='Target (7.0)')
    plt.xlabel('Pattern')
    plt.ylabel('Average Quality Score')
    plt.title('Quality Comparison by Pattern')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def plot_cost_comparison(df: pd.DataFrame, output_path: str):
    """Save a bar chart of average cost by pattern.

    Args:
        df: Dataframe with at least 'pattern' and 'avg_cost' columns.
        output_path: File path to save the resulting image.
    """
    plt.figure(figsize=(10, 6))
    plt.bar(df['pattern'], df['avg_cost'])
    plt.axhline(y=2.0, color='r', linestyle='--', label='Target (€2.0)')
    plt.xlabel('Pattern')
    plt.ylabel('Cost per Post (EUR)')
    plt.title('Cost Comparison by Pattern')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def plot_cost_vs_quality(df: pd.DataFrame, output_path: str):
    """Save a scatter plot comparing cost vs quality.

    Adds target threshold lines for quick visual inspection.

    Args:
        df: Dataframe with 'pattern', 'avg_cost', and 'avg_quality' columns.
        output_path: File path to save the resulting image.
    """
    plt.figure(figsize=(10, 8))
    plt.scatter(df['avg_cost'], df['avg_quality'], s=200)

    for i, pattern in enumerate(df['pattern']):
        plt.annotate(pattern, (df['avg_cost'].iloc[i], df['avg_quality'].iloc[i]))

    plt.axhline(y=7.0, color='r', linestyle='--', alpha=0.5, label='Quality target')
    plt.axvline(x=2.0, color='r', linestyle='--', alpha=0.5, label='Cost target')
    plt.xlabel('Cost per Post (EUR)')
    plt.ylabel('Average Quality Score')
    plt.title('Cost vs Quality Trade-off')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def calculate_quality_per_euro(avg_quality: float, avg_cost: float) -> float:
    """Calculate an efficiency metric: quality per euro.

    Args:
        avg_quality: Average quality score for a pattern.
        avg_cost: Average cost for the same pattern (EUR).

    Returns:
        The ratio avg_quality / avg_cost, or 0 if avg_cost is 0.
    """
    quality = avg_quality / avg_cost if avg_cost > 0 else 0
    return quality
