import html as _html
import io
import json
import os
import re
import sys
import threading
import time
from contextlib import redirect_stderr, redirect_stdout

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

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

st.set_page_config(page_title="Trial Architect", page_icon="🧬", layout="wide", initial_sidebar_state="collapsed")

# ===========================================================================
# DESIGN SYSTEM
# ===========================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Instrument+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
:root{--bg:#F3F6FB;--surface:#fff;--ink:#0F1B33;--muted:#5B6885;--line:#E1E8F3;--accent:#2545F4;--accent2:#00B8A9;--warn:#F5A524;--good:#12B76A;--bad:#E5484D;
--shadow:0 1px 2px rgba(15,27,51,.04),0 12px 32px -12px rgba(37,69,244,.18);}
html,body,[class*="css"],.stApp{font-family:'Instrument Sans',sans-serif;color:var(--ink);}
h1,h2,h3,h4{font-family:'Bricolage Grotesque',sans-serif !important;letter-spacing:-.02em;color:var(--ink);}
header[data-testid="stHeader"],footer,#MainMenu,[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stSidebarCollapsedControl"]{display:none !important;}
.block-container{max-width:1160px;padding:2.2rem 1.5rem 5rem !important;}
.stApp{background:var(--bg);}
.stApp::before,.stApp::after{content:"";position:fixed;z-index:0;border-radius:50%;filter:blur(90px);pointer-events:none;opacity:.55;}
.stApp::before{width:520px;height:520px;background:#CFDAFF;top:-140px;right:-100px;animation:drift 18s ease-in-out infinite alternate;}
.stApp::after{width:460px;height:460px;background:#C6F3EC;bottom:-160px;left:-120px;animation:drift 22s ease-in-out infinite alternate-reverse;}
@keyframes drift{to{transform:translate(-60px,50px) scale(1.15);}}
.main .block-container{position:relative;z-index:1;}
@keyframes rise{from{opacity:0;transform:translateY(22px);}to{opacity:1;transform:none;}}
@keyframes fade{from{opacity:0}to{opacity:1}}

/* top bar */
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:2rem;animation:fade .8s both;}
.brand{display:flex;align-items:center;gap:.7rem;font-family:'Bricolage Grotesque';font-weight:800;font-size:1.15rem;}
.logo{width:36px;height:36px;border-radius:11px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:grid;place-items:center;color:#fff;box-shadow:0 8px 20px -6px var(--accent);animation:spin-in 1s cubic-bezier(.2,.9,.3,1.2) both;}
@keyframes spin-in{from{transform:rotate(-180deg) scale(.3);opacity:0}}
.status{display:flex;align-items:center;gap:.5rem;padding:.4rem .9rem;background:#fff;border:1px solid var(--line);border-radius:99px;font-size:.85rem;font-weight:500;color:var(--muted);}
.dot{width:8px;height:8px;border-radius:50%;background:var(--warn);}
.dot.on{background:var(--good);animation:pulse 2s infinite;}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(18,183,106,.55)}70%,100%{box-shadow:0 0 0 9px rgba(18,183,106,0)}}

/* hero */
.hero{text-align:center;max-width:820px;margin:0 auto 1.6rem;}
.hero h1{font-size:clamp(2.2rem,5.5vw,4rem);line-height:1.04;font-weight:800;margin:0 0 .9rem;padding:0;background:linear-gradient(100deg,#0F1B33 20%,#2545F4 55%,#00B8A9 85%);background-size:200% auto;-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;animation:shine 6s linear infinite,rise .9s .1s cubic-bezier(.2,.8,.2,1) both;}
@keyframes shine{to{background-position:200% center;}}
.hero p{font-size:1.1rem;color:var(--muted);line-height:1.6;animation:rise .9s .25s both;}

/* navigation (radio -> big step cards) */
div[role="radiogroup"]{display:grid !important;grid-template-columns:repeat(4,1fr);gap:.8rem;counter-reset:n;margin:1.4rem 0 1.6rem;}
div[role="radiogroup"]>label{counter-increment:n;display:flex !important;align-items:center;gap:.75rem;margin:0 !important;padding:1rem 1.1rem !important;background:#fff;border:1.5px solid var(--line);border-radius:18px;cursor:pointer;transition:all .3s cubic-bezier(.2,.8,.2,1);animation:rise .6s both;}
div[role="radiogroup"]>label:nth-child(2){animation-delay:.06s}div[role="radiogroup"]>label:nth-child(3){animation-delay:.12s}div[role="radiogroup"]>label:nth-child(4){animation-delay:.18s}
div[role="radiogroup"]>label>div:first-of-type{display:none !important;}
div[role="radiogroup"]>label::before{content:counter(n);flex:none;width:28px;height:28px;border-radius:10px;background:#EEF2FF;color:var(--accent);display:grid;place-items:center;font-weight:700;font-size:.82rem;transition:all .3s;}
div[role="radiogroup"]>label p{font-family:'Bricolage Grotesque';font-weight:700;font-size:1.02rem;color:var(--muted);margin:0;transition:color .3s;}
div[role="radiogroup"]>label:hover{transform:translateY(-3px);border-color:#BFCBF5;box-shadow:var(--shadow);}
div[role="radiogroup"]>label:has(input:checked){border-color:var(--accent);background:linear-gradient(180deg,#fff,#EEF2FF);box-shadow:0 14px 30px -14px rgba(37,69,244,.55);}
div[role="radiogroup"]>label:has(input:checked)::before{background:var(--accent);color:#fff;transform:rotate(-8deg) scale(1.08);}
div[role="radiogroup"]>label:has(input:checked) p{color:var(--ink);}
@media(max-width:760px){div[role="radiogroup"]{grid-template-columns:repeat(2,1fr);}}

/* cards + headings */
[data-testid="stVerticalBlockBorderWrapper"]{background:#fff;border:1px solid var(--line) !important;border-radius:24px !important;box-shadow:var(--shadow);padding:.9rem 1.1rem;animation:rise .55s cubic-bezier(.2,.8,.2,1) both;}
.section-title{font-family:'Bricolage Grotesque';font-weight:800;font-size:1.7rem;letter-spacing:-.02em;margin:0 0 .25rem;}
.section-sub{color:var(--muted);margin:0 0 1.2rem;line-height:1.55;max-width:70ch;}

/* inputs / buttons */
.stTextArea textarea{border-radius:16px !important;border:1.5px solid var(--line) !important;background:#FAFBFF !important;padding:1rem !important;font-size:1rem;line-height:1.55;transition:all .25s;}
.stTextArea textarea:focus{border-color:var(--accent) !important;box-shadow:0 0 0 4px rgba(37,69,244,.12) !important;background:#fff !important;}
.stButton>button,.stDownloadButton>button{border-radius:14px;height:3rem;padding:0 1.6rem;font-weight:600;border:1.5px solid var(--line);background:#fff;color:var(--ink);transition:all .25s cubic-bezier(.2,.8,.2,1);}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);border-color:var(--accent);color:var(--accent);box-shadow:0 10px 22px -10px rgba(37,69,244,.5);}
.stButton>button:active{transform:scale(.97);}
.stButton>button[kind="primary"]{color:#fff;border:none;background:linear-gradient(120deg,#2545F4,#5B3DF5 50%,#00B8A9);background-size:200% auto;box-shadow:0 12px 26px -10px rgba(37,69,244,.7);}
.stButton>button[kind="primary"]:hover{color:#fff;background-position:right center;}
[data-testid="stExpander"]{border:1px solid var(--line) !important;border-radius:16px !important;background:#FAFBFF;overflow:hidden;margin-top:.6rem;}
[data-testid="stExpander"] summary{font-weight:600;padding:.8rem 1rem;}
[data-testid="stAlert"]{border-radius:16px;}
code{background:#EEF2FF;color:var(--accent);padding:.1rem .4rem;border-radius:6px;font-size:.85em;}
:focus-visible{outline:3px solid rgba(37,69,244,.4);outline-offset:2px;}

/* ===== LIVE RUN MONITOR ===== */
.mon{position:relative;margin-top:1.2rem;padding:1.3rem 1.4rem 1.2rem;border-radius:20px;background:linear-gradient(180deg,#FBFCFF,#F3F6FF);border:1px solid #D9E2F8;overflow:hidden;}
.mon.done{background:linear-gradient(180deg,#FBFFFD,#F1FBF6);border-color:#CDEEDD;}
.mon.err{background:#FFF8F8;border-color:#F6D0D2;}
.mon-head{display:flex;align-items:center;gap:.9rem;}
.orb{position:relative;flex:none;width:40px;height:40px;border-radius:50%;background:conic-gradient(from 0deg,var(--accent),var(--accent2),var(--accent));animation:spin 1.2s linear infinite;animation-delay:var(--d);}
.orb::after{content:"";position:absolute;inset:6px;background:#F6F8FF;border-radius:50%;}
.mon.done .orb{animation:none;background:var(--good);display:grid;place-items:center;}
.mon.done .orb::after{content:"✓";position:static;background:none;color:#fff;font-weight:800;font-size:1.1rem;}
.mon.err .orb{animation:none;background:var(--bad);}
.mon.err .orb::after{content:"!";position:static;background:none;color:#fff;font-weight:800;display:grid;place-items:center;height:100%;}
@keyframes spin{to{transform:rotate(360deg)}}
.mon-title{font-family:'Bricolage Grotesque';font-weight:700;font-size:1.15rem;line-height:1.2;}
.mon-phase{color:var(--muted);font-size:.9rem;}
.mon-time{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:.85rem;color:var(--muted);background:#fff;border:1px solid var(--line);padding:.25rem .6rem;border-radius:9px;}
.prog{position:relative;height:5px;border-radius:9px;background:#E3E9F8;margin:1rem 0 1.1rem;overflow:hidden;}
.prog::after{content:"";position:absolute;top:0;bottom:0;width:38%;border-radius:9px;background:linear-gradient(90deg,transparent,var(--accent),var(--accent2),transparent);animation:sweep 1.6s ease-in-out infinite;animation-delay:var(--d);}
.mon.done .prog::after,.mon.err .prog::after{display:none;}
.mon.done .prog{background:var(--good);}
@keyframes sweep{from{left:-40%}to{left:102%}}
.tl{position:relative;display:flex;flex-direction:column;gap:.15rem;margin-bottom:1rem;}
.tl-row{display:flex;align-items:center;gap:.7rem;padding:.35rem 0;font-size:.95rem;}
.tl-ic{flex:none;width:22px;height:22px;border-radius:50%;background:var(--good);color:#fff;font-size:.72rem;font-weight:800;display:grid;place-items:center;}
.tl-row.act .tl-ic{background:none;border:2.5px solid #C9D5F7;border-top-color:var(--accent);animation:spin 1.2s linear infinite;animation-delay:var(--d);}
.tl-row.act .tl-name{font-weight:600;}
.tl-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.tl-t{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--muted);}
.feed{font-family:'JetBrains Mono',monospace;font-size:.78rem;line-height:1.75;background:#fff;border:1px solid var(--line);border-radius:14px;padding:.7rem .9rem;color:#42516F;max-height:190px;overflow:hidden;}
.feed div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:.55;}
.feed div:last-child{opacity:1;color:var(--ink);}
.feed div:last-child::after{content:"▍";color:var(--accent);margin-left:2px;animation:blink 1s steps(2) infinite;}
.mon.done .feed div:last-child::after,.mon.err .feed div:last-child::after{content:"";}
@keyframes blink{50%{opacity:0}}
.feed-h{font-size:.8rem;font-weight:600;color:var(--muted);margin:.2rem 0 .4rem;}

/* score rings */
.rings{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;margin:.4rem 0 1rem;}
.ring{background:#FAFBFF;border:1px solid var(--line);border-radius:20px;padding:1.2rem 1rem;text-align:center;transition:transform .3s,box-shadow .3s;}
.ring:hover{transform:translateY(-4px);box-shadow:var(--shadow);}
.ring svg{width:96px;height:96px;transform:rotate(-90deg);}
.ring .track{fill:none;stroke:#E6ECF6;stroke-width:8;}
.ring .bar{fill:none;stroke:var(--c);stroke-width:8;stroke-linecap:round;stroke-dasharray:213.6;stroke-dashoffset:213.6;animation:fill 1.4s .2s cubic-bezier(.2,.8,.2,1) forwards;}
@keyframes fill{to{stroke-dashoffset:var(--off);}}
.ring .num{font-family:'Bricolage Grotesque';font-weight:800;font-size:1.6rem;margin-top:-68px;height:68px;line-height:68px;}
.ring .lbl{margin-top:.9rem;font-weight:600;color:var(--muted);font-size:.9rem;}
.chips{display:flex;gap:.5rem;flex-wrap:wrap;margin:.2rem 0 1rem;}
.tag{display:inline-block;padding:.25rem .75rem;border-radius:99px;background:#E9EEFF;color:var(--accent);font-size:.82rem;font-weight:600;}
.tag.g{background:#E3F7EC;color:#0B7A47;}.tag.w{background:#FFF1DB;color:#9A5B00;}

/* gene pool */
.gp{width:100%;border-collapse:separate;border-spacing:0 8px;}
.gp th{text-align:left;font-size:.8rem;color:var(--muted);font-weight:600;padding:0 .8rem;}
.gp td{background:#FAFBFF;padding:.8rem;border-top:1px solid var(--line);border-bottom:1px solid var(--line);}
.gp td:first-child{border-left:1px solid var(--line);border-radius:14px 0 0 14px;font-weight:700;}
.gp td:last-child{border-right:1px solid var(--line);border-radius:0 14px 14px 0;}
.gp tr{animation:rise .5s both;}
.mini{position:relative;height:6px;background:#E6ECF6;border-radius:9px;overflow:hidden;min-width:60px;}
.mini i{position:absolute;inset:0 auto 0 0;border-radius:9px;background:linear-gradient(90deg,var(--accent),var(--accent2));animation:grow 1s cubic-bezier(.2,.8,.2,1) both;}
@keyframes grow{from{width:0 !important}}
.mini-v{font-size:.78rem;font-weight:600;color:var(--muted);margin-bottom:4px;}

/* empty + init */
.empty{text-align:center;padding:2.4rem 1rem;color:var(--muted);}
.empty .ico{font-size:2.2rem;display:inline-block;animation:bob 3s ease-in-out infinite;}
@keyframes bob{50%{transform:translateY(-8px)}}
.empty h4{margin:.6rem 0 .2rem;}
.check{display:flex;gap:.7rem;align-items:flex-start;padding:.7rem 0;border-bottom:1px dashed var(--line);color:var(--muted);font-size:.95rem;}
.check:last-child{border:none;}.check span{color:var(--good);font-weight:800;}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none !important;transition:none !important;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ===========================================================================
# LIVE RUN MONITOR: shows what the system is doing, as it happens
# Runs the work in a background thread, captures everything printed to the
# terminal, and redraws a progress card while the main thread waits.
# ===========================================================================
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_CURRENT = {"mon": None}


def note(step_name: str):
    """Mark a step as finished on the live monitor (no-op if none is running)."""
    if _CURRENT["mon"] is not None:
        _CURRENT["mon"].step(step_name)


def pretty(name: str) -> str:
    return str(name).replace("_", " ").replace("-", " ").strip().capitalize()


class Monitor:
    def __init__(self, title: str):
        self.title, self.phase, self.active = title, "Starting up", "Warming up..."
        self.ph = st.empty()
        self.t0 = time.time()
        self.steps, self.log, self.state = [], [], "run"
        self.buf, self.lock = "", threading.Lock()

    def feed(self, text: str):
        with self.lock:
            self.buf += text
            parts = re.split(r"[\r\n]+", self.buf)
            self.buf = parts.pop()
            for p in parts:
                p = _ANSI.sub("", p).strip()
                if p:
                    self.log.append(p)
                    self.active = p

    def step(self, name: str):
        with self.lock:
            self.steps.append((name, time.time() - self.t0))

    def set_phase(self, phase: str):
        with self.lock:
            self.phase = phase

    def render(self):
        with self.lock:
            el = time.time() - self.t0
            esc = _html.escape
            rows = "".join(
                f'<div class="tl-row"><div class="tl-ic">✓</div><div class="tl-name">{esc(n)}</div><div class="tl-t">{t:.0f}s</div></div>'
                for n, t in self.steps[-6:]
            )
            if self.state == "run":
                rows += (
                    f'<div class="tl-row act"><div class="tl-ic"></div><div class="tl-name">{esc(self.phase)}</div>'
                    f'<div class="tl-t">working</div></div>'
                )
            feed = "".join(f"<div>{esc(l[:160])}</div>" for l in self.log[-6:]) or "<div>Waiting for first output</div>"
            sub = {"run": self.phase, "done": f"Finished in {el:.0f} seconds", "err": "Something went wrong"}[self.state]
            cls = {"run": "", "done": "done", "err": "err"}[self.state]
            d = -(el % 4.8)
            self.ph.markdown(
                f'<div class="mon {cls}" style="--d:{d:.2f}s"><div class="mon-head"><div class="orb"></div>'
                f'<div><div class="mon-title">{esc(self.title)}</div><div class="mon-phase">{esc(sub)}</div></div>'
                f'<div class="mon-time">{int(el//60):02d}:{int(el%60):02d}</div></div><div class="prog"></div>'
                f'<div class="tl">{rows}</div><div class="feed-h">Live activity</div><div class="feed">{feed}</div></div>',
                unsafe_allow_html=True,
            )


class _Tee(io.TextIOBase):
    encoding = "utf-8"  # class attribute: io.TextIOBase's own 'encoding' can't be set on instances
    errors = "replace"

    def __init__(self, mon, orig):
        self.mon, self.orig = mon, orig

    def write(self, s):
        self.mon.feed(s)
        try:
            self.orig.write(s)
        except Exception:
            pass
        return len(s)

    def flush(self):
        try:
            self.orig.flush()
        except Exception:
            pass

    def isatty(self):
        return False


def run_monitored(title: str, fn):
    """Run fn(mon) in a worker thread while showing live progress. Returns fn's result."""
    mon = Monitor(title)
    _CURRENT["mon"] = mon
    out = {}

    def target():
        try:
            out["r"] = fn(mon)
        except BaseException as e:  # noqa
            out["e"] = e

    th = threading.Thread(target=target, daemon=True)
    add_script_run_ctx(th, get_script_run_ctx())
    tee = _Tee(mon, sys.__stdout__)
    with redirect_stdout(tee), redirect_stderr(tee):
        th.start()
        while th.is_alive():
            mon.render()
            time.sleep(0.4)
    _CURRENT["mon"] = None
    mon.state = "err" if "e" in out else "done"
    mon.render()
    if "e" in out:
        st.error(f"{type(out['e']).__name__}: {out['e']}")
        return None
    return out.get("r")


def run_graph(graph, inputs, mon):
    """Stream the LangGraph run so each node shows up live; fall back to invoke()."""
    state, got_any = None, False
    try:
        for mode, chunk in graph.stream(inputs, stream_mode=["updates", "values"]):
            got_any = True
            if mode == "updates":
                for node, upd in (chunk or {}).items():
                    names = []
                    if isinstance(upd, dict):
                        names = [getattr(o, "agent_name", None) for o in (upd.get("agent_outputs") or [])]
                    names = [n for n in names if n]
                    mon.step(f"{pretty(node)} finished" + (f" ({', '.join(names)})" if names else ""))
                    mon.set_phase("Passing results to the next agent")
            else:
                state = chunk
    except Exception:
        if got_any:
            raise
        state = None
    return state if state is not None else graph.invoke(inputs)


# ===========================================================================
# UI helpers
# ===========================================================================
def topbar(ready: bool):
    label = "System ready" if ready else "Not initialized"
    st.markdown(
        f'<div class="topbar"><div class="brand"><div class="logo">🧬</div>Trial Architect</div>'
        f'<div class="status"><span class="dot {"on" if ready else ""}"></span>{label}</div></div>',
        unsafe_allow_html=True,
    )


def section(title, sub=""):
    st.markdown(f'<div class="section-title">{title}</div><p class="section-sub">{sub}</p>', unsafe_allow_html=True)


def empty(icon, title, msg):
    st.markdown(f'<div class="empty"><div class="ico">{icon}</div><h4>{title}</h4><div>{msg}</div></div>', unsafe_allow_html=True)


def ring(label, score):
    pct = max(0.0, min(1.0, float(score)))
    color = "#12B76A" if pct >= 0.75 else "#2545F4" if pct >= 0.5 else "#F5A524"
    return (
        f'<div class="ring"><svg viewBox="0 0 80 80"><circle class="track" cx="40" cy="40" r="34"/>'
        f'<circle class="bar" cx="40" cy="40" r="34" style="--c:{color};--off:{213.6*(1-pct):.1f}"/></svg>'
        f'<div class="num">{score:.2f}</div><div class="lbl">{label}</div></div>'
    )


def mini(v):
    return f'<div class="mini-v">{v:.2f}</div><div class="mini"><i style="width:{max(0,min(1,v))*100:.0f}%"></i></div>'


# ===========================================================================
# One-time setup (cached across reruns)
# ===========================================================================
@st.cache_resource(show_spinner=False)
def setup_system():
    load_environment()
    llm_config = get_llm_config()
    note("Loaded environment and model settings")

    create_data_directories()

    pubmed_query = "(SGLT2 inhibitor) AND (type 2 diabetes) AND (renal impairment)"
    download_pubmed_articles(pubmed_query)
    note("Downloaded PubMed research articles")

    fda_url = "https://www.fda.gov/media/71185/download"
    fda_pdf_path = os.path.join(data_paths["fda"], "fda_diabetes_guidance.pdf")
    download_and_extract_text_from_pdf(fda_url, fda_pdf_path)
    note("Read the FDA diabetes guidance")

    create_ethics_document()
    note("Prepared the ethics reference")

    db_path = load_real_mimic_data()
    note("Loaded MIMIC patient data")

    knowledge_stores = create_retrievers(llm_config["embedding_model"], db_path)
    note("Built the searchable knowledge stores")

    guild_agents.configure(llm_config, knowledge_stores)
    evaluators_module.configure(llm_config)
    director_agents.configure(llm_config)

    guild_graph = build_guild_graph()
    note("Assembled the Guild graph")
    return guild_graph, db_path


ready = "guild_graph" in st.session_state
topbar(ready)

st.markdown(
    '<div class="hero"><h1>Trial criteria that improve themselves</h1>'
    "<p>A guild of AI specialists drafts inclusion and exclusion criteria, scores them on five pillars, "
    "and evolves its own playbook to do better next time.</p></div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Start screen (replaces the sidebar)
# ---------------------------------------------------------------------------
if not ready:
    _, mid, _ = st.columns([1, 2.2, 1])
    with mid:
        with st.container(border=True):
            section("Get started", "Check these, then load everything in one click. You'll see each step as it happens.")
            st.markdown(
                '<div class="check"><span>✓</span><div>Ollama is running locally</div></div>'
                '<div class="check"><span>✓</span><div>Models pulled: <code>llama3.1:8b-instruct</code> <code>qwen2:7b</code> '
                '<code>llama3:70b</code> <code>nomic-embed-text</code></div></div>'
                '<div class="check"><span>✓</span><div>Your <code>.env</code> file has <code>ENTREZ_EMAIL</code> set</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Load data and build the Guild", type="primary", use_container_width=True):
                res = run_monitored("Building the Guild", lambda mon: (mon.set_phase("Loading data sources and models"), setup_system())[1])
                if res:
                    st.session_state["guild_graph"], st.session_state["db_path"] = res
                    st.session_state["gene_pool"] = SOPGenePool()
                    time.sleep(0.8)
                    st.rerun()
    st.stop()

guild_graph = st.session_state["guild_graph"]
gene_pool: SOPGenePool = st.session_state["gene_pool"]

nav = st.radio(
    "Step",
    ["✍️  Draft", "🧪  Evaluate", "🧬  Evolve", "🎯  Frontier"],
    horizontal=True,
    label_visibility="collapsed",
    key="nav",
)

default_request = (
    "Draft inclusion/exclusion criteria for a Phase II trial of 'Sotagliflozin', a novel "
    "SGLT2 inhibitor, for adults with uncontrolled Type 2 Diabetes (HbA1c > 8.0%) and "
    "moderate chronic kidney disease (CKD Stage 3)."
)

# ---------------------------------------------------------------------------
# 1. Draft
# ---------------------------------------------------------------------------
if nav.strip().endswith("Draft"):
    with st.container(border=True):
        section("Describe your trial", "The Guild reads your concept, researches it, and drafts inclusion and exclusion criteria.")
        trial_request = st.text_area("Trial concept", value=default_request, height=120, label_visibility="collapsed")

        if st.button("Draft criteria", type="primary"):
            baseline_sop = build_baseline_sop()
            need_baseline = not gene_pool.pool

            def draft_work(mon):
                mon.set_phase("Planner and specialists are working")
                state = run_graph(guild_graph, {"initial_request": trial_request, "sop": baseline_sop}, mon)
                mon.step("Criteria drafted")
                ev = None
                if need_baseline:
                    mon.set_phase("Scoring the first draft on five pillars")
                    ev = run_full_evaluation(state)
                    mon.step("Baseline scored")
                return state, ev

            res = run_monitored("Drafting your criteria", draft_work)
            if res:
                final_state, eval_result = res
                st.session_state["last_final_state"] = final_state
                st.session_state["trial_request"] = trial_request
                if eval_result is not None:
                    gene_pool.add(sop=baseline_sop, eval_result=eval_result)
                    st.session_state["last_eval"] = eval_result
                st.toast("Criteria drafted", icon="✅")

    if "last_final_state" in st.session_state:
        with st.container(border=True):
            section("Generated criteria")
            criteria = st.session_state["last_final_state"]["final_criteria"]
            st.markdown(criteria)
            st.download_button("Download as Markdown", criteria, file_name="trial_criteria.md")
            with st.expander("Specialist outputs"):
                for out in st.session_state["last_final_state"]["agent_outputs"]:
                    st.markdown(f"**{out.agent_name}**")
                    st.text(out.findings[:2000])

# ---------------------------------------------------------------------------
# 2. Evaluate
# ---------------------------------------------------------------------------
elif nav.strip().endswith("Evaluate"):
    with st.container(border=True):
        section("Evaluation gauntlet", "Every draft is scored from 0 to 1 on five pillars.")
        if "last_final_state" not in st.session_state:
            empty("📝", "Nothing to score yet", "Draft criteria in the Draft step first.")
        else:
            if st.button("Score latest draft", type="primary"):
                def eval_work(mon):
                    mon.set_phase("Judging rigor, compliance, ethics, feasibility and simplicity")
                    r = run_full_evaluation(st.session_state["last_final_state"])
                    mon.step("All five pillars scored")
                    return r

                r = run_monitored("Scoring the draft", eval_work)
                if r:
                    st.session_state["last_eval"] = r

            if "last_eval" in st.session_state:
                evals = st.session_state["last_eval"]
                labels = ["Rigor", "Compliance", "Ethics", "Feasibility", "Simplicity"]
                values = [evals.rigor, evals.compliance, evals.ethics, evals.feasibility, evals.simplicity]
                scores = [v.score for v in values]
                best, worst = labels[scores.index(max(scores))], labels[scores.index(min(scores))]
                st.markdown(
                    f'<div class="chips"><span class="tag">Average {sum(scores)/5:.2f}</span>'
                    f'<span class="tag g">Strongest: {best}</span><span class="tag w">Needs work: {worst}</span></div>'
                    '<div class="rings">' + "".join(ring(l, s) for l, s in zip(labels, scores)) + "</div>",
                    unsafe_allow_html=True,
                )
                for label, val in zip(labels, values):
                    with st.expander(f"Why {label.lower()} scored {val.score:.2f}"):
                        st.write(val.reasoning)

# ---------------------------------------------------------------------------
# 3. Evolve
# ---------------------------------------------------------------------------
elif nav.strip().endswith("Evolve"):
    with st.container(border=True):
        section("Evolve the Guild", "The Director finds the weakest pillar, writes 2–3 improved playbooks, runs the Guild with each, and scores the results.")
        if not gene_pool.pool:
            empty("🌱", "The gene pool is empty", "Draft criteria once to plant the first version.")
        else:
            if st.button("Run one evolution cycle", type="primary"):
                req = st.session_state.get("trial_request", default_request)

                def evolve_work(mon):
                    mon.set_phase("Director is diagnosing the weakest pillar and mutating the SOP")
                    run_evolution_cycle(gene_pool, req, guild_graph)
                    mon.step("New SOP versions generated and scored")

                run_monitored("Evolving the Guild", evolve_work)
                st.toast(f"Gene pool now has {len(gene_pool.pool)} versions", icon="🧬")

            rows = ""
            for i, entry in enumerate(gene_pool.pool):
                e = entry["evaluation"]
                parent = '<span class="tag">root</span>' if entry["parent"] is None else f'v{entry["parent"]}'
                cells = "".join(f"<td>{mini(v.score)}</td>" for v in (e.rigor, e.compliance, e.ethics, e.feasibility, e.simplicity))
                rows += f'<tr style="animation-delay:{i*80}ms"><td>v{entry["version"]}</td><td>{parent}</td>{cells}</tr>'
            st.markdown(
                '<table class="gp"><tr><th>Version</th><th>Parent</th><th>Rigor</th><th>Compliance</th>'
                f"<th>Ethics</th><th>Feasibility</th><th>Simplicity</th></tr>{rows}</table>",
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# 4. Frontier
# ---------------------------------------------------------------------------
else:
    with st.container(border=True):
        section("Pareto frontier", "Versions that no other version beats on every pillar at once.")
        if not gene_pool.pool:
            empty("🎯", "No versions to compare", "Draft criteria, then run an evolution cycle.")
        else:
            pareto_sops = identify_pareto_front(gene_pool)
            st.markdown(
                f'<div class="chips"><span class="tag">{len(pareto_sops)} of {len(gene_pool.pool)} versions are non-dominated</span></div>',
                unsafe_allow_html=True,
            )
            fig = visualize_frontier(pareto_sops)
            if fig is not None:
                st.pyplot(fig)
            with st.expander("View SOP JSON for each optimal version"):
                for entry in pareto_sops:
                    st.markdown(f"**SOP v{entry['version']}**")
                    st.json(json.loads(entry["sop"].json()))