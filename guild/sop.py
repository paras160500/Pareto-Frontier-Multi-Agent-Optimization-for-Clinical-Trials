"""
    The Guild's SOP
    This Pydantic model is the configuration object the Outer Loop(Ai REsearch Director)
    evolves generation after generation
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

from typing import Literal
from pydantic import BaseModel, Field 


# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Schema / func Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

class GuildSOP(BaseModel):
    """Standard Operating Procedures for the Trial Design Guild."""
    planner_prompt: str = Field(description="The system prompt for the Planner Agent.")
    researcher_retriever_k: int = Field(description="Number of documents for the Medical Researcher to retrieve.", default=3)
    synthesizer_prompt: str = Field(description="The system prompt for the Criteria Synthesizer Agent.")
    synthesizer_model: Literal["gpt-4o-mini", "gpt-5-mini"] = Field(description="The LLM to use for the Synthesizer.", default="gpt-4o-mini")
    use_sql_analyst: bool = Field(description="Whether to use the Patient Cohort Analyst agent.", default=True)
    use_ethics_specialist: bool = Field(description="Whether to use the Ethics Specialist agent.", default=True)


def build_baseline_sop() -> GuildSOP:
    """Version 1.0 SOP — the starting point for evolution, identical to the notebook baseline."""
    return GuildSOP(
        planner_prompt=(
            "You are a master planner for clinical trial design. Your task is to receive a "
            "high-level trial concept and break it down into a structured plan with specific "
            "sub-tasks for a team of specialists: a Regulatory Specialist, a Medical Researcher, "
            "an Ethics Specialist, and a Patient Cohort Analyst. Output a JSON object with a "
            "single key 'plan' containing a list of tasks. Each task must have 'agent', "
            "'task_description', and 'dependencies' keys."
        ),
        synthesizer_prompt=(
            "You are an expert medical writer. Your task is to synthesize the structured findings "
            "from all specialist teams into a formal 'Inclusion and Exclusion Criteria' document. "
            "Be concise, precise, and adhere strictly to the information provided. Structure your "
            "output into two sections: 'Inclusion Criteria' and 'Exclusion Criteria'."
        ),
        researcher_retriever_k=3,
        synthesizer_model="gpt-4o-mini",
        use_sql_analyst=True,
        use_ethics_specialist=True,
    )
