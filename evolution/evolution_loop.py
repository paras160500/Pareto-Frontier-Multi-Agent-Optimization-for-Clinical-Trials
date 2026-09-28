"""
    The full evolutionary Loop

    One generation is Diagnose -> Evolve -> Evluate, executed aginst the latest gene-pool entry.
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

from evolution.gene_pool import SOPGenePool
from evolution.director_agents import performance_diagnostician, sop_architect
from evalution.gauntlet import run_full_evaluation


# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                       logic Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

def run_evolution_cycle(gene_pool: SOPGenePool, trial_request: str, guild_graph) -> None:
    """Runs one full cycle of diagnosis, mutation, and evaluation."""
    print("\n" + "=" * 25 + " STARTING NEW EVOLUTION CYCLE " + "=" * 25)

    # 1. Select the current best SOP to improve upon (simplified: take the latest)
    current_best_entry = gene_pool.get_latest_entry()
    parent_sop = current_best_entry["sop"]
    parent_eval = current_best_entry["evaluation"]
    parent_version = current_best_entry["version"]
    print(f"Improving upon SOP v{parent_version}...")

    # 2. Diagnose the problem
    diagnosis = performance_diagnostician(parent_eval)
    print(f"Diagnosis complete. Primary Weakness: '{diagnosis.primary_weakness}'. Recommendation: {diagnosis.recommendation}")

    # 3. Architect new SOPs
    new_sop_candidates = sop_architect(diagnosis, parent_sop)
    print(f"Generated {len(new_sop_candidates.mutations)} new SOP candidates.")

    # 4. Evaluate each new candidate
    for i, candidate_sop in enumerate(new_sop_candidates.mutations):
        print(f"\n--- Testing SOP candidate {i + 1}/{len(new_sop_candidates.mutations)} ---")
        guild_input = {"initial_request": trial_request, "sop": candidate_sop}
        final_state = guild_graph.invoke(guild_input)

        eval_result = run_full_evaluation(final_state)
        gene_pool.add(sop=candidate_sop, eval_result=eval_result, parent_version=parent_version)

    print("\n" + "=" * 25 + " EVOLUTION CYCLE COMPLETE " + "=" * 26)