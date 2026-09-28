"""
    Pareto Frontier navigation.
    - identify_pareto_front : finds non-dominated SOPs
    - visualize_frontier : 2D scatter (Rigor vs Feasibility) + parallel coordinates plot
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

from typing import List, Dict, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from evolution.gene_pool import SOPGenePool


# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Logic and Graph creat Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

def identify_pareto_front(gene_pool: SOPGenePool) -> List[Dict[str, Any]]:
    """Identifies the non-dominated solutions in the gene pool."""
    pareto_front = []
    pool_entries = gene_pool.pool

    for i, candidate in enumerate(pool_entries):
        is_dominated = False
        cand_scores = np.array(
            [s["score"] for s in candidate["evaluation"].model_dump().values()]
        )

        for j, other in enumerate(pool_entries):
            if i == j:
                continue
            other_scores = np.array(
                [s["score"] for s in other["evaluation"].model_dump().values()]
            )

            # 'other' dominates 'candidate' if it's better or equal on all scores,
            # and strictly better on at least one.
            if np.all(other_scores >= cand_scores) and np.any(other_scores > cand_scores):
                is_dominated = True
                break

        if not is_dominated:
            pareto_front.append(candidate)

    return pareto_front


def visualize_frontier(pareto_sops: List[Dict[str, Any]]):
    """Creates a 2D scatter plot and parallel coordinates plot."""

    if not pareto_sops:
        print("No SOPs on the Pareto front to visualize.")
        return None

    labels = [f"v{s['version']}" for s in pareto_sops]
    rigor_scores = [s["evaluation"].rigor.score for s in pareto_sops]
    feasibility_scores = [s["evaluation"].feasibility.score for s in pareto_sops]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # ---------------------------------------------------------
    # 2D scatter
    # ---------------------------------------------------------
    ax1.scatter(
        rigor_scores,
        feasibility_scores,
        s=150,
        alpha=0.7
    )

    for i, txt in enumerate(labels):
        ax1.annotate(
            txt,
            (rigor_scores[i], feasibility_scores[i]),
            xytext=(10, -10),
            textcoords="offset points",
            fontsize=12
        )

    ax1.set_title(
        "Pareto Frontier: Rigor vs. Feasibility",
        fontsize=14
    )
    ax1.set_xlabel("Scientific Rigor Score", fontsize=12)
    ax1.set_ylabel("Recruitment Feasibility Score", fontsize=12)
    ax1.grid(True, linestyle="--", alpha=0.6)

    # Avoid identical min/max axis limits
    if min(rigor_scores) == max(rigor_scores):
        ax1.set_xlim(
            min(rigor_scores) - 0.05,
            max(rigor_scores) + 0.05
        )
    else:
        ax1.set_xlim(
            min(rigor_scores) - 0.05,
            max(rigor_scores) + 0.05
        )

    if min(feasibility_scores) == max(feasibility_scores):
        ax1.set_ylim(
            min(feasibility_scores) - 0.1,
            max(feasibility_scores) + 0.1
        )
    else:
        ax1.set_ylim(
            min(feasibility_scores) - 0.1,
            max(feasibility_scores) + 0.1
        )

    # ---------------------------------------------------------
    # Parallel coordinates
    # ---------------------------------------------------------
    data = []

    for s in pareto_sops:
        eval_dict = s["evaluation"].model_dump()

        scores = {
            k: v["score"]
            for k, v in eval_dict.items()
        }

        scores["SOP Version"] = f"v{s['version']}"
        data.append(scores)

    df = pd.DataFrame(data)

    pd.plotting.parallel_coordinates(
        df,
        class_column="SOP Version",
        colormap=plt.get_cmap("viridis"),
        ax=ax2
    )

    ax2.set_title(
        "5D Performance Trade-offs on Pareto Front",
        fontsize=14
    )
    ax2.grid(
        True,
        which="major",
        axis="y",
        linestyle="--",
        alpha=0.6
    )
    ax2.set_ylabel("Normalized Score", fontsize=12)
    ax2.legend(loc="upper right")

    plt.tight_layout()

    return fig
