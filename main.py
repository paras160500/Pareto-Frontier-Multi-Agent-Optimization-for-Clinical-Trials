"""
    CLI entrypoint.

    Runs the exact same end-to-end flow as the notebook, top to bottom:
    1. Load environment + LLM foundry
    2. Build data directories and download/prepare all four knowledge sources
    3. Build vector stores / retrievers
    4. Compile the Guild graph
    5. Run one full Guild pass on a test trial request
    6. Run the evaluation gauntlet on the baseline result
    7. Seed the gene pool and run one evolution cycle
    8. Identify and visualize the Pareto front

    Usage:
        python main.py
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

import os
import json

from config.settings import load_environment
from config.llm_foundry import get_llm_config

from data_pipeline.paths import data_paths, create_data_directories
from data_pipeline.pubmed_loader import download_pubmed_articles
from data_pipeline.fda_loader import download_and_extract_text_from_pdf
from data_pipeline.ethics_loader import create_ethics_document
from data_pipeline.mimic_loader import load_real_mimic_data, preview_mimic_db
from data_pipeline.vector_store import create_retrievers

from guild.sop import build_baseline_sop
from guild import agents as guild_agents
from guild.graph import build_guild_graph

from evalution import evaluators as evaluators_module
from evalution.gauntlet import run_full_evaluation

from evolution.gene_pool import SOPGenePool
from evolution import director_agents
from evolution.evolution_loop import run_evolution_cycle
from evolution.pareto import identify_pareto_front, visualize_frontier

TEST_REQUEST = (
    "Draft inclusion/exclusion criteria for a Phase II trial of 'Sotagliflozin', a novel "
    "SGLT2 inhibitor, for adults with uncontrolled Type 2 Diabetes (HbA1c > 8.0%) and "
    "moderate chronic kidney disease (CKD Stage 3)."
)


# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   main logic Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

def setup_knowledge_stores(llm_config: dict) -> dict:
    """Steps 1.4.1 - 1.4.6: build every data source and the retrievers on top of them."""
    create_data_directories()

    pubmed_query = "(SGLT2 inhibitor) AND (type 2 diabetes) AND (renal impairment)"
    download_pubmed_articles(pubmed_query)

    fda_url = "https://www.fda.gov/media/168475/download"
    fda_pdf_path = os.path.join(
        data_paths["fda"],
        "fda_diabetes_guidance.pdf"
    )

    download_and_extract_text_from_pdf(
        fda_url,
        fda_pdf_path
    )

    create_ethics_document()

    db_path = load_real_mimic_data()
    if db_path:
        print(f"Real MIMIC-III database created at: {db_path}")
        preview_mimic_db(db_path)
    else:
        print("Skipping MIMIC preview — files not found. The Cohort Analyst will fail unless you add them.")

    return create_retrievers(llm_config["embedding_model"], db_path)


def main():
    load_environment()
    llm_config = get_llm_config()

    knowledge_stores = setup_knowledge_stores(llm_config)

    # Inject shared config/state into the modules that need it (mirrors the notebook's globals)
    guild_agents.configure(llm_config, knowledge_stores)
    evaluators_module.configure(llm_config)
    director_agents.configure(llm_config)

    guild_graph = build_guild_graph()

    # --- Part 2.4: full test run of the baseline Guild ---
    print("Running the full Guild graph with baseline SOP v1.0...")
    baseline_sop = build_baseline_sop()
    graph_input = {"initial_request": TEST_REQUEST, "sop": baseline_sop}
    final_result = guild_graph.invoke(graph_input)

    print("\nFinal Guild Output:")
    print("---------------------")
    print(final_result["final_criteria"])

    # --- Part 3: evaluate the baseline ---
    baseline_evaluation_result = run_full_evaluation(final_result)
    print("\nFull Evaluation Result for Baseline SOP:")
    print(json.dumps(baseline_evaluation_result.dict(), indent=4))

    # --- Part 4: seed gene pool and run one evolution cycle ---
    gene_pool = SOPGenePool()
    print("Initialized SOP Gene Pool.")
    gene_pool.add(sop=baseline_sop, eval_result=baseline_evaluation_result)

    run_evolution_cycle(gene_pool, TEST_REQUEST, guild_graph)

    print("\nSOP Gene Pool Evaluation Summary:")
    print("---------------------------------")
    for entry in gene_pool.pool:
        v = entry["version"]
        p = entry["parent"]
        evals = entry["evaluation"]
        r, c, e, f, s = evals.rigor.score, evals.compliance.score, evals.ethics.score, evals.feasibility.score, evals.simplicity.score
        parent_str = "(Parent)" if p is None else f"(Child of v{p})"
        print(f"SOP v{v:<2} {parent_str:<14}: Rigor={r:.2f}, Compliance={c:.2f}, Ethics={e:.2f}, Feasibility={f:.2f}, Simplicity={s:.2f}")

    # --- Part 5: Pareto front ---
    pareto_sops = identify_pareto_front(gene_pool)
    print("\nSOPs on the Pareto Front:")
    print("-------------------------")
    for entry in pareto_sops:
        v = entry["version"]
        evals = entry["evaluation"]
        r, c, e, f, s = evals.rigor.score, evals.compliance.score, evals.ethics.score, evals.feasibility.score, evals.simplicity.score
        print(f"SOP v{v}: Rigor={r:.2f}, Compliance={c:.2f}, Ethics={e:.2f}, Feasibility={f:.2f}, Simplicity={s:.2f}")

    fig = visualize_frontier(pareto_sops)
    if fig is not None:
        out_path = "pareto_frontier.png"
        fig.savefig(out_path, dpi=150)
        print(f"\nSaved Pareto frontier plot to {out_path}")


if __name__ == "__main__":
    main()