"""
    Aggregate the evaluation gaunlet

    Runs all five evaluators against a completed Guild run and returns the 5D 
    performance vector the outer loop needs
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

from pydantic import BaseModel

from guild.state import GuildState
from evalution.evaluators import (
    GradedScore,
    scientific_rigor_evaluator,
    regulatory_compliance_evaluator,
    ethical_soundness_evaluator,
    feasibility_evaluator,
    simplicity_evaluator,
)

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Evaluation  Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

class EvaluationResult(BaseModel):
    rigor: GradedScore
    compliance: GradedScore
    ethics: GradedScore
    feasibility: GradedScore
    simplicity: GradedScore


def run_full_evaluation(guild_final_state: GuildState) -> EvaluationResult:
    print("--- RUNNING FULL EVALUATION GAUNTLET ---")
    final_criteria = guild_final_state["final_criteria"]
    agent_outputs = guild_final_state["agent_outputs"]

    pubmed_context = next((o.findings for o in agent_outputs if o.agent_name == "Medical Researcher"), "")
    fda_context = next((o.findings for o in agent_outputs if o.agent_name == "Regulatory Specialist"), "")
    ethics_context = next((o.findings for o in agent_outputs if o.agent_name == "Ethics Specialist"), "")
    analyst_output = next((o for o in agent_outputs if o.agent_name == "Patient Cohort Analyst"), None)

    print("Evaluating: Scientific Rigor...")
    rigor = scientific_rigor_evaluator(final_criteria, pubmed_context)
    print("Evaluating: Regulatory Compliance...")
    compliance = regulatory_compliance_evaluator(final_criteria, fda_context)
    print("Evaluating: Ethical Soundness...")
    ethics = ethical_soundness_evaluator(final_criteria, ethics_context)
    print("Evaluating: Recruitment Feasibility...")
    feasibility = feasibility_evaluator(analyst_output) if analyst_output else GradedScore(score=0, reasoning="Analyst did not run.")
    print("Evaluating: Operational Simplicity...")
    simplicity = simplicity_evaluator(final_criteria)

    print("--- EVALUATION GAUNTLET COMPLETE ---")
    return EvaluationResult(rigor=rigor, compliance=compliance, ethics=ethics, feasibility=feasibility, simplicity=simplicity)