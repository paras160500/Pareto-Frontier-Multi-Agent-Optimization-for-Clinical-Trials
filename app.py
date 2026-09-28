import json
import os

import streamlit as st

from config.settings import load_environment
from config.llm_foundry import get_llm_config

from data_pipeline.paths import data_paths
from data_pipeline.pubmed_loader import download_pubmed_articles
from data_pipeline.fda_loader import download_and_extract_text_from_pdf
from data_pipeline.ethics_loader import create_ethics_document
from data_pipeline.mimic_loader import load_real_mimic_data
from data_pipeline.vector_store import create_retrievers
from data_pipeline.paths import create_data_directories

from guild.sop import build_baseline_sop, GuildSOP
from guild import agents as guild_agents
from guild.graph import build_guild_graph

from evalution import evaluators as evaluators_module
from evalution.gauntlet import run_full_evaluation

from evolution.gene_pool import SOPGenePool
from evolution import director_agents
from evolution.evolution_loop import run_evolution_cycle
from evolution.pareto import identify_pareto_front, visualize_frontier

st.set_page_config(page_title="AI Clinical Trials Architect", layout="wide")
st.title("🧬 AI Clinical Trials Architect")
st.caption("A self-evolving multi-agent guild that drafts clinical trial inclusion/exclusion criteria.")


# ---------------------------------------------------------------------------
# One-time setup, cached across reruns in this session
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Setting up knowledge stores, models, and the Guild graph...")
def setup_system():
    load_environment()
    llm_config = get_llm_config()

    create_data_directories()

    pubmed_query = "(SGLT2 inhibitor) AND (type 2 diabetes) AND (renal impairment)"
    download_pubmed_articles(pubmed_query)

    fda_url = "https://www.fda.gov/media/71185/download"
    fda_pdf_path = os.path.join(data_paths["fda"], "fda_diabetes_guidance.pdf")
    download_and_extract_text_from_pdf(fda_url, fda_pdf_path)

    create_ethics_document()

    db_path = load_real_mimic_data()

    knowledge_stores = create_retrievers(llm_config["embedding_model"], db_path)

    guild_agents.configure(llm_config, knowledge_stores)
    evaluators_module.configure(llm_config)
    director_agents.configure(llm_config)

    guild_graph = build_guild_graph()
    return guild_graph, db_path


with st.sidebar:
    st.header("Setup")
    st.write(
        "Before running, make sure Ollama is running locally with the required models pulled "
        "(`llama3.1:8b-instruct`, `qwen2:7b`, `llama3:70b`, `nomic-embed-text`), and that your "
        "`.env` file has `ENTREZ_EMAIL` set."
    )
    if st.button("Initialize system", type="primary"):
        st.session_state["guild_graph"], st.session_state["db_path"] = setup_system()
        st.session_state["gene_pool"] = SOPGenePool()
        st.success("System initialized.")

if "guild_graph" not in st.session_state:
    st.info("Click **Initialize system** in the sidebar to load data sources, models, and build the Guild graph.")
    st.stop()

guild_graph = st.session_state["guild_graph"]
gene_pool: SOPGenePool = st.session_state["gene_pool"]

tab_draft, tab_eval, tab_evolve, tab_pareto = st.tabs(
    ["1. Draft Criteria", "2. Evaluation Gauntlet", "3. Evolve the Guild", "4. Pareto Frontier"]
)

# ---------------------------------------------------------------------------
# Tab 1: Draft criteria with the baseline (or latest) Guild SOP
# ---------------------------------------------------------------------------
with tab_draft:
    st.subheader("Draft Inclusion / Exclusion Criteria")
    default_request = (
        "Draft inclusion/exclusion criteria for a Phase II trial of 'Sotagliflozin', a novel "
        "SGLT2 inhibitor, for adults with uncontrolled Type 2 Diabetes (HbA1c > 8.0%) and "
        "moderate chronic kidney disease (CKD Stage 3)."
    )
    trial_request = st.text_area("Trial concept", value=default_request, height=100)

    if st.button("Run the Trial Design Guild"):
        baseline_sop = build_baseline_sop()
        with st.spinner("Planner -> Specialists -> Synthesizer..."):
            final_state = guild_graph.invoke({"initial_request": trial_request, "sop": baseline_sop})
        st.session_state["last_final_state"] = final_state
        st.session_state["trial_request"] = trial_request

        if not gene_pool.pool:
            with st.spinner("Running evaluation gauntlet on baseline..."):
                eval_result = run_full_evaluation(final_state)
            gene_pool.add(sop=baseline_sop, eval_result=eval_result)
            st.session_state["last_eval"] = eval_result

    if "last_final_state" in st.session_state:
        st.markdown("### Generated Criteria")
        st.markdown(st.session_state["last_final_state"]["final_criteria"])

        with st.expander("Specialist agent outputs (raw)"):
            for out in st.session_state["last_final_state"]["agent_outputs"]:
                st.markdown(f"**{out.agent_name}**")
                st.text(out.findings[:2000])

# ---------------------------------------------------------------------------
# Tab 2: Evaluation gauntlet on the latest run
# ---------------------------------------------------------------------------
with tab_eval:
    st.subheader("Multi-Dimensional Evaluation Gauntlet")
    if "last_final_state" not in st.session_state:
        st.info("Run the Guild in Tab 1 first.")
    else:
        if st.button("Run evaluation on latest draft"):
            with st.spinner("Scoring rigor, compliance, ethics, feasibility, simplicity..."):
                eval_result = run_full_evaluation(st.session_state["last_final_state"])
            st.session_state["last_eval"] = eval_result

        if "last_eval" in st.session_state:
            evals = st.session_state["last_eval"]
            cols = st.columns(5)
            labels = ["Rigor", "Compliance", "Ethics", "Feasibility", "Simplicity"]
            values = [evals.rigor, evals.compliance, evals.ethics, evals.feasibility, evals.simplicity]
            for col, label, val in zip(cols, labels, values):
                col.metric(label, f"{val.score:.2f}")
            for label, val in zip(labels, values):
                with st.expander(f"{label} reasoning"):
                    st.write(val.reasoning)

# ---------------------------------------------------------------------------
# Tab 3: Run an evolution cycle
# ---------------------------------------------------------------------------
with tab_evolve:
    st.subheader("AI Research Director: Evolve the Guild's SOP")
    st.write(
        "This diagnoses the weakest pillar of the latest gene-pool entry, generates 2-3 mutated "
        "SOPs to address it, runs the Guild with each, and scores them."
    )
    if not gene_pool.pool:
        st.info("Run the Guild at least once in Tab 1 to seed the gene pool first.")
    else:
        if st.button("Run one evolution cycle"):
            with st.spinner("Diagnosing weaknesses and evolving the SOP..."):
                run_evolution_cycle(gene_pool, st.session_state.get("trial_request", default_request), guild_graph)
            st.success(f"Gene pool now has {len(gene_pool.pool)} SOP versions.")

        if gene_pool.pool:
            st.markdown("### Gene Pool Summary")
            rows = []
            for entry in gene_pool.pool:
                evals = entry["evaluation"]
                rows.append({
                    "Version": f"v{entry['version']}",
                    "Parent": "—" if entry["parent"] is None else f"v{entry['parent']}",
                    "Rigor": round(evals.rigor.score, 2),
                    "Compliance": round(evals.compliance.score, 2),
                    "Ethics": round(evals.ethics.score, 2),
                    "Feasibility": round(evals.feasibility.score, 2),
                    "Simplicity": round(evals.simplicity.score, 2),
                })
            st.dataframe(rows, use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 4: Pareto frontier
# ---------------------------------------------------------------------------
with tab_pareto:
    st.subheader("5D Pareto Frontier")
    if not gene_pool.pool:
        st.info("Run the Guild and at least one evolution cycle first.")
    else:
        pareto_sops = identify_pareto_front(gene_pool)
        st.write(f"{len(pareto_sops)} of {len(gene_pool.pool)} SOPs are non-dominated (on the Pareto front).")

        fig = visualize_frontier(pareto_sops)
        if fig is not None:
            st.pyplot(fig)

        with st.expander("View raw SOP JSON for each Pareto-optimal version"):
            for entry in pareto_sops:
                st.markdown(f"**SOP v{entry['version']}**")
                st.json(json.loads(entry["sop"].json()))