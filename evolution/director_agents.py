"""
    The director-level agents - the brain of the Outer loop

    This will perform the below things
    - performance_diagnostician : analyze the 5D scorecard, finds the biggest weakness
    - sop_architect : mutates the SOP to try to fix that weakness
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

from typing import List, Literal
from pydantic import BaseModel, Field 
from langchain_core.prompts import ChatPromptTemplate

from guild.sop import GuildSOP
from evalution.gauntlet import EvaluationResult

llm_config = None 


# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                       Logic Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

def configure(llm_config_in: dict) -> None:
    global llm_config
    llm_config = llm_config_in


class Diagnosis(BaseModel):
    primary_weakness: Literal["rigor", "compliance", "ethics", "feasibility", "simplicity"]
    root_cause_analysis: str = Field(description="A detailed analysis of why the weakness occurred, referencing specific scores.")
    recommendation: str = Field(description="A high-level recommendation for how to modify the SOP to address the weakness.")


def performance_diagnostician(eval_result: EvaluationResult) -> Diagnosis:
    """Analyzes the 5D evaluation vector and diagnoses the primary weakness."""
    print("--- EXECUTING PERFORMANCE DIAGNOSTICIAN ---")
    diagnostician_llm = llm_config["director"].with_structured_output(Diagnosis)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a world-class management consultant specializing in process optimization. Your task is to analyze a performance scorecard and identify the single biggest weakness. Then, provide a root cause analysis and a strategic recommendation."),
        ("human", "Please analyze the following performance evaluation report:\n\n{report}"),
    ])

    chain = prompt | diagnostician_llm
    return chain.invoke({"report": eval_result.model_dump_json()})


class EvolvedSOPs(BaseModel):
    """A container for a list of new, evolved GuildSOPs."""
    mutations: List[GuildSOP]


def sop_architect(diagnosis: Diagnosis, current_sop: GuildSOP) -> EvolvedSOPs:
    """Takes a diagnosis and the current SOP, and generates new, mutated SOPs."""
    print("--- EXECUTING SOP ARCHITECT ---")
    architect_llm = llm_config["director"].with_structured_output(EvolvedSOPs)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            f"You are an AI process architect. Your job is to modify a process configuration (an SOP) "
            f"to fix a diagnosed problem. The SOP is a JSON object with this schema: "
            f"{GuildSOP.model_json_schema()}. You must return a list of 2-3 new, valid SOP JSON objects "
            f"under the 'mutations' key. Propose diverse and creative mutations. For example, you can "
            f"change prompts, toggle agents, change retrieval parameters, or even change the model "
            f"used for a task. Only modify fields relevant to the diagnosis.",
        ),
        ("human", "Here is the current SOP:\n{current_sop}\n\nHere is the performance diagnosis:\n{diagnosis}\n\nBased on the diagnosis, please generate 2-3 new, improved SOPs."),
    ])

    chain = prompt | architect_llm
    return chain.invoke({"current_sop": current_sop.model_dump_json(), "diagnosis": diagnosis.model_dump_json()})