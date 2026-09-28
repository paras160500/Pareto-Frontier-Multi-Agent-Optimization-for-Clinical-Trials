"""
    Multi0Dimensional Evluation Gauntlet - Individual evaluators
    Three are LLM-as-Judge using the director model, two are programmatic.
"""

from pydantic import BaseModel, Field 
from langchain_core.prompts import ChatPromptTemplate

from guild.state import AgentOutput

llm_config = None 

def configure(llm_config_in : dict) -> None:
    global llm_config 
    llm_config = llm_config_in

class GradedScore(BaseModel):
    score : float = Field(description="A Score from 0.0 to 1.0")
    reasoning : str = Field(description="A brief justification for the score.")

# Evaluator 1 : Scientific Rigor(LLM-as-Judge)
def scientific_rigor_evaluator(generated_criteria: str, pubmed_context: str) -> GradedScore:
    evaluator_llm = llm_config["director"].with_structured_output(GradedScore)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert clinical scientist. Evaluate a set of clinical trial criteria based on the provided scientific literature. A score of 1.0 means the criteria are perfectly aligned with and justified by the literature. A score of 0.0 means they contradict or ignore the literature."),
        ("human", "Evaluate the following criteria:\n\n**Generated Criteria:**\n{criteria}\n\n**Supporting Scientific Context:**\n{context}"),
    ])
    chain = prompt | evaluator_llm
    return chain.invoke({"criteria": generated_criteria, "context": pubmed_context})


# Evluator 2 : Regulatory Compliance (LLM-as-Judge)
def regulatory_compliance_evaluator(generated_criteria: str, fda_context: str) -> GradedScore:
    evaluator_llm = llm_config["director"].with_structured_output(GradedScore)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert regulatory affairs specialist. Evaluate if a set of clinical trial criteria adheres to the provided FDA guidelines. A score of 1.0 means full compliance."),
        ("human", "Evaluate the following criteria:\n\n**Generated Criteria:**\n{criteria}\n\n**Applicable FDA Guidelines:**\n{context}"),
    ])
    chain = prompt | evaluator_llm
    return chain.invoke({"criteria": generated_criteria, "context": fda_context})


# Evaluator 3: Ethical Soundness (LLM-as-Judge)
def ethical_soundness_evaluator(generated_criteria: str, ethics_context: str) -> GradedScore:
    evaluator_llm = llm_config["director"].with_structured_output(GradedScore)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert on clinical trial ethics. Evaluate if a set of criteria adheres to the ethical principles provided (summarizing the Belmont Report). A score of 1.0 means the criteria show strong respect for persons, beneficence, and justice."),
        ("human", "Evaluate the following criteria:\n\n**Generated Criteria:**\n{criteria}\n\n**Ethical Principles:**\n{context}"),
    ])
    chain = prompt | evaluator_llm
    return chain.invoke({"criteria": generated_criteria, "context": ethics_context})


# Evaluator 4: Recruitment Feasibility (Programmatic)
def feasibility_evaluator(cohort_analyst_output: AgentOutput) -> GradedScore:
    findings_text = cohort_analyst_output.findings
    try:
        count_str = findings_text.split("database: ")[1].replace(".", "")
        patient_count = int(count_str)
    except (IndexError, ValueError):
        return GradedScore(score=0.0, reasoning="Could not parse patient count from analyst output.")
    # Normalize score. Ideal target for a Phase II trial is ~150 patients.
    IDEAL_COUNT = 150.0
    score = min(1.0, patient_count / IDEAL_COUNT)
    reasoning = f"Estimated {patient_count} eligible patients. Score is normalized against an ideal target of {int(IDEAL_COUNT)}."
    return GradedScore(score=score, reasoning=reasoning)


# Evaluator 5: Operational Simplicity (Programmatic)
def simplicity_evaluator(generated_criteria: str) -> GradedScore:
    EXPENSIVE_TESTS = ["mri", "genetic sequencing", "pet scan", "biopsy", "echocardiogram", "endoscopy"]
    test_count = sum(1 for test in EXPENSIVE_TESTS if test in generated_criteria.lower())
    score = max(0.0, 1.0 - (test_count * 0.5))
    reasoning = f"Found {test_count} expensive/complex screening procedures mentioned."
    return GradedScore(score=score, reasoning=reasoning)