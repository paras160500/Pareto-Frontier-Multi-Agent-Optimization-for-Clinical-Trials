"""
    Guild Specialist agentns
    - planner_agent -> The planner
    - retrieval_Agent -> generic retriever used by regulator/Medical/ethics
    - patient_cohort_analyst -> text-to-SQL feasibility analyst
    - criteria_synthesizer -> final writer
"""

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                   Import / Init Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

import json 
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import duckdb
from pydantic import BaseModel, Field
from typing import List
from guild.state import GuildState , AgentOutput

class PlannerTask(BaseModel):
    agent: str = Field(
        description="The specialist agent responsible for this task."
    )
    task_description: str = Field(
        description="The specific task the specialist must perform."
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Tasks that must be completed before this task."
    )


class PlannerOutput(BaseModel):
    plan: List[PlannerTask] = Field(
        description="A list of specialist tasks required to complete the clinical trial criteria task."
    )




llm_config = None 
knowledge_stores = None 

# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚
#                                       Agent Statements
# ✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚✚

def configure(llm_config_in : dict , knowledge_stores_in : dict) -> None:
    """
        Wire in the model usite and retrievers build during the setup. Call once at startup
    """
    global llm_config , knowledge_stores
    llm_config = llm_config_in
    knowledge_stores = knowledge_stores_in


def planner_agent(state: GuildState) -> GuildState:
    """
    Receives the initial request and creates a plan.
    """
    print("-----EXECUTING PLANNER AGENT-----")

    sop = state["sop"]

    print("Creating structured planner LLM...")
    planner_llm = llm_config["planner"].with_structured_output(
        PlannerOutput
    )

    prompt = (
        f"{sop.planner_prompt}\n\n"
        f"Trial Concept: {state['initial_request']}"
    )

    print(f"Planner Prompt:\n{prompt}")
    print(">>> BEFORE PLANNER LLM INVOKE")

    response = planner_llm.invoke(prompt)

    print(">>> AFTER PLANNER LLM INVOKE")
    print(f"Generated Plan:\n{response.model_dump()}")

    return {
        **state,
        "plan": response.model_dump()["plan"]
    }



def retrieval_agent(task_description : str , state : GuildState , retriever_name : str , agent_name : str) -> AgentOutput:
    """
        Generic Agent to perform retrieval from a specified vector store.
    """
    print(f"----- EXECUTING {agent_name.upper()} -----")
    print(f"Task : {task_description}")
    retriever = knowledge_stores[retriever_name]

    # Handle dynamic 'k' for researcher
    if agent_name == "Medical Researcher":
        retriever.search_kwargs["k"] = state["sop"].researcher_retriever_k
        print(f"Using k={state['sop'].researcher_retriever_k} for retrieval.")

    retrieved_docs = retriever.invoke(task_description)

    findings = "\n\n---\n\n".join(
        [f"Source: {doc.metadata.get('source', 'N/A')}\n\n{doc.page_content}" for doc in retrieved_docs]
    )
    print(f"Retrieved {len(retrieved_docs)} documents.")
    print(f"Sample Finding:\n{findings[:500]}...")
    return AgentOutput(agent_name=agent_name, findings=findings)


def patient_cohort_analyst(task_description: str, state: GuildState) -> AgentOutput:
    """Estimates cohort size by generating and executing a SQL query against the MIMIC database."""
    print("--- EXECUTING PATIENT COHORT ANALYST ---")
    if not state["sop"].use_sql_analyst:
        return AgentOutput(agent_name="Patient Cohort Analyst", findings="Analysis skipped as per SOP.")

    # Get DB schema for context
    con = duckdb.connect(knowledge_stores["mimic_db_path"])
    schema_query = """
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'main' ORDER BY table_name, column_name;
    """
    schema = con.execute(schema_query).df()
    con.close()

    sql_generation_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            f"You are an expert SQL writer specializing in DuckDB... The database contains patient "
            f"data with the following schema:\\n{schema.to_string()}\\n\\nIMPORTANT: All column names "
            f"in your query MUST be uppercase (e.g., SELECT SUBJECT_ID, ICD9_CODE...).\\n\\nKey "
            f"Mappings:\\n- T2DM (Type 2 Diabetes) corresponds to ICD9_CODE '25000'.\\n- Moderate renal "
            f"impairment can be estimated by a creatinine lab value (ITEMID 50912) where VALUENUM is "
            f"between 1.5 and 3.0.\\n- Uncontrolled T2D can be estimated by an HbA1c lab value "
            f"(ITEMID 50852) where VALUENUM is greater than 8.0.",
        ),
        ("human", "Please write a SQL query to count the number of unique patients who meet the following criteria: {task}"),
    ])

    sql_chain = sql_generation_prompt | llm_config["sql_coder"] | StrOutputParser()

    print(f"Generating SQL for task: {task_description}")
    sql_query = sql_chain.invoke({"task": task_description})

    # Clean up potential markdown formatting from the LLM
    sql_query = sql_query.strip().replace("```sql", "").replace("```", "")
    print(f"Generated SQL Query:\n{sql_query}")

    try:
        con = duckdb.connect(knowledge_stores["mimic_db_path"])
        result = con.execute(sql_query).fetchone()
        patient_count = result[0] if result else 0
        con.close()

        findings = f"Generated SQL Query:\n{sql_query}\n\nEstimated eligible patient count from the synthetic database: {patient_count}."
        print(f"Query executed successfully. Estimated patient count: {patient_count}")
    except Exception as e:
        findings = f"Error executing SQL query: {e}. Defaulting to a count of 0."
        print(f"Error during query execution: {e}")

    return AgentOutput(agent_name="Patient Cohort Analyst", findings=findings)


def criteria_synthesizer(state: GuildState) -> GuildState:
    """Synthesizes all findings into the final criteria document."""
    print("--- EXECUTING CRITERIA SYNTHESIZER ---")
    sop = state["sop"]
    drafter_llm = ChatOpenAI(model=sop.synthesizer_model, temperature=0.2)

    context = "\n\n---\n\n".join(
        [f"**{out.agent_name} Findings:**\n{out.findings}" for out in state["agent_outputs"]]
    )

    prompt = f"{sop.synthesizer_prompt}\n\n**Context from Specialist Teams:**\n{context}"
    print(f"Synthesizer is using model '{sop.synthesizer_model}'.")

    response = drafter_llm.invoke(prompt)
    print("Final criteria generated.")

    return {
        **state,
        "final_criteria": response.content
    }