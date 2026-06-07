import config
import os
import re
import plotly.graph_objects as go
from collections import defaultdict

import streamlit as st
from app.db_connector import SQLServerConnector
from rules.rule_loader import RuleLoader
from validators.validation_engine import ValidationEngine
from validators.batch_validator import BatchValidator
from validators.rule_mapper import RuleMapper
from validators.export_manager import ExportManager, _friendly_expected
from validators.data_doctor_router import DataDoctor
from utils.models import BatchValidationReport, TableValidationReport
from dotenv import load_dotenv

load_dotenv()

# ── CSS ──────────────────────────────────────────────────────────────────────
_CSS = """
section.main > div { padding-top: .8rem; }
[data-testid="stSidebar"] { border-right: 1px solid rgba(99,102,241,.18) !important; }

/* metric cards */
[data-testid="metric-container"] {
    border: 1px solid rgba(99,102,241,.25) !important;
    border-radius: 12px !important; padding: 16px 20px !important;
    transition: border-color .2s, transform .2s, box-shadow .2s;
}
[data-testid="metric-container"]:hover {
    border-color: rgba(99,102,241,.6) !important; transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(99,102,241,.14);
}
[data-testid="stMetricValue"] { font-size:1.75rem !important; font-weight:700 !important; }
[data-testid="stMetricLabel"] { font-size:.72rem !important; text-transform:uppercase !important; letter-spacing:.05em !important; opacity:.7 !important; }

/* buttons */
.stButton > button {
    background: linear-gradient(135deg,#4f46e5,#6366f1) !important;
    color: #fff !important; border: none !important; border-radius: 8px !important;
    font-weight: 500 !important; transition: transform .15s, box-shadow .15s !important;
}
.stButton > button:hover { transform:translateY(-1px) !important; box-shadow:0 4px 14px rgba(99,102,241,.38) !important; }
.stButton > button:active { transform:translateY(0) !important; }

/* download buttons */
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg,#065f46,#047857) !important;
    color: #fff !important; border: none !important; border-radius: 6px !important;
    font-size: .78rem !important; padding: 4px 10px !important;
    transition: transform .15s, box-shadow .15s !important;
}
[data-testid="stDownloadButton"] > button:hover { transform:translateY(-1px) !important; box-shadow:0 4px 12px rgba(4,120,87,.3) !important; }

/* expander */
[data-testid="stExpander"] { border: 1px solid rgba(99,102,241,.22) !important; border-radius: 10px !important; }
summary { font-weight: 600 !important; }

/* form */
[data-testid="stForm"] { border: 1px solid rgba(99,102,241,.22) !important; border-radius: 10px !important; padding: 12px !important; }

/* inputs */
.stTextInput > div > div > input { border-radius: 8px !important; transition: border-color .2s, box-shadow .2s !important; }
.stTextInput > div > div > input:focus { border-color: #6366f1 !important; box-shadow: 0 0 0 3px rgba(99,102,241,.15) !important; }

/* chat messages */
[data-testid="stChatMessage"] { border: 1px solid rgba(99,102,241,.18) !important; border-radius: 12px !important; margin: 6px 0 !important; }

/* divider */
hr { border-color: rgba(99,102,241,.18) !important; }

/* dataframe */
tbody tr:hover { background: rgba(99,102,241,.05) !important; }

/* severity chips */
.chip-critical { display:inline-block; background:rgba(239,68,68,.12);  color:#dc2626; border:1px solid rgba(239,68,68,.35);  border-radius:6px; padding:2px 8px; font-size:.72rem; font-weight:600; }
.chip-warning  { display:inline-block; background:rgba(245,158,11,.12); color:#d97706; border:1px solid rgba(245,158,11,.35); border-radius:6px; padding:2px 8px; font-size:.72rem; font-weight:600; }
.chip-info     { display:inline-block; background:rgba(59,130,246,.12);  color:#2563eb; border:1px solid rgba(59,130,246,.35);  border-radius:6px; padding:2px 8px; font-size:.72rem; font-weight:600; }

/* page title */
.page-title {
    background: rgba(99,102,241,.07);
    border: 1px solid rgba(99,102,241,.28); border-radius: 14px;
    padding: 20px 28px; margin-bottom: 16px;
}
.page-title h1 {
    margin:0; font-size:1.55rem; font-weight:700;
    background: linear-gradient(90deg,#6366f1,#a78bfa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.page-title p { margin:4px 0 0 0; font-size:.82rem; opacity:.55; }

/* ── DataDoctor animated orb ── */
.dd-orb-wrap { display:flex; align-items:center; gap:16px; margin-bottom:14px; }
.dd-orb { position:relative; width:56px; height:56px; flex-shrink:0; }
.orb-core {
    position:absolute; inset:10px; border-radius:50%;
    background:linear-gradient(135deg,#4f46e5,#7c3aed);
    display:flex; align-items:center; justify-content:center; z-index:3;
    animation:orb-breathe 3s ease-in-out infinite;
}
.orb-ring { position:absolute; border-radius:50%; border:1.5px solid rgba(99,102,241,.45); animation:orb-pulse 2.6s ease-out infinite; }
.r1 { inset:2px;   animation-delay:0s; }
.r2 { inset:-5px;  animation-delay:.75s; }
.r3 { inset:-12px; animation-delay:1.5s; }
@keyframes orb-pulse  { 0%{opacity:.8;transform:scale(1)} 100%{opacity:0;transform:scale(1.28)} }
@keyframes orb-breathe {
    0%,100%{ filter:brightness(1);    box-shadow:0 0 6px 2px rgba(99,102,241,.2); }
    50%    { filter:brightness(1.28); box-shadow:0 0 18px 6px rgba(99,102,241,.45); }
}
/* thinking state — faster & more intense */
.dd-orb.thinking .orb-ring  { animation-duration:.85s; border-color:rgba(139,92,246,.75); }
.dd-orb.thinking .orb-core  { background:linear-gradient(135deg,#7c3aed,#a855f7); animation-duration:.85s; }
.dd-orb-info strong { font-size:1.05rem; }
.dd-model-tag { font-size:.72rem; opacity:.6; font-family:monospace; margin-top:2px; }

/* analyzing badge */
@keyframes analyzing { 0%,100%{opacity:1} 50%{opacity:.55} }
.analyzing-badge {
    display:inline-flex; align-items:center; gap:8px;
    background:rgba(99,102,241,.12); color:#6366f1;
    padding:5px 12px; border-radius:20px; font-size:.74rem; font-weight:500;
    border:1px solid rgba(99,102,241,.3); animation:analyzing 1.5s ease-in-out infinite;
}

/* AI status badge (idle) */
@keyframes ai-pulse { 0%{box-shadow:0 0 0 0 rgba(99,102,241,.5)} 70%{box-shadow:0 0 0 8px rgba(99,102,241,0)} 100%{box-shadow:0 0 0 0 rgba(99,102,241,0)} }
.ai-badge {
    display:inline-flex; align-items:center; gap:6px;
    background:linear-gradient(135deg,#4f46e5,#7c3aed); color:#fff;
    padding:4px 12px; border-radius:20px; font-size:.72rem; font-weight:600;
    letter-spacing:.04em; animation:ai-pulse 2.5s infinite;
}
"""


# ── helpers ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _fetch_ollama_models(url: str) -> list:
    try:
        import requests
        r = requests.get(f"{url.rstrip('/')}/api/tags", timeout=5)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return []


def _ensure_data_doctor():
    if not st.session_state.get("data_doctor_enabled"):
        return None
    backend = st.session_state.get("llm_backend", "ollama")
    current = st.session_state.get("data_doctor")
    if backend == "ollama":
        model = st.session_state.get("ollama_model") or "llama3"
        url   = st.session_state.get("ollama_url", "http://localhost:11434")
        if current is None or current.backend != backend or current.model != model:
            st.session_state.data_doctor = DataDoctor(backend="ollama", model=model, ollama_url=url)
    elif backend == "groq":
        model = st.session_state.get("groq_model", DataDoctor.GROQ_MODELS[0])
        key   = st.session_state.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")
        if current is None or current.backend != backend or current.model != model:
            st.session_state.data_doctor = DataDoctor(backend="groq", model=model, groq_api_key=key)
    return st.session_state.data_doctor


def _dd_orb(backend: str, model: str, thinking: bool = False) -> str:
    ml = model.split("/")[-1] if "/" in model else model
    cls = "dd-orb thinking" if thinking else "dd-orb"
    status = '<div class="analyzing-badge" style="margin-top:5px;font-size:.7rem;">⚡ Generating…</div>' if thinking else ""
    return f"""
<div class="dd-orb-wrap">
  <div class="{cls}">
    <div class="orb-ring r1"></div><div class="orb-ring r2"></div><div class="orb-ring r3"></div>
    <div class="orb-core">
      <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
        <path d="M12 2a5 5 0 1 1 0 10A5 5 0 0 1 12 2zm0 12c5.33 0 8 2.67 8 4v2H4v-2c0-1.33 2.67-4 8-4z"
              fill="white" opacity=".9"/>
        <circle cx="19" cy="6" r="3" fill="#a78bfa"/>
        <path d="M16.5 6 Q18 4 19 6 Q20 8 19 9" stroke="white" stroke-width="1.2" fill="none"/>
      </svg>
    </div>
  </div>
  <div class="dd-orb-info">
    <strong>🤖 DataDoctor</strong>
    <div class="dd-model-tag">{backend} · {ml}</div>
    {status}
  </div>
</div>"""


# ── chart builders ────────────────────────────────────────────────────────────

def _chart_severity(n_crit, n_warn, n_info):
    total = n_crit + n_warn + n_info
    if not total:
        return None
    fig = go.Figure(go.Pie(
        labels=["CRITICAL","WARNING","INFO"], values=[n_crit,n_warn,n_info], hole=.55,
        marker=dict(colors=["#ef4444","#f59e0b","#3b82f6"], line=dict(color="#080c14",width=2)),
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center", font=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=30,l=0,r=0), height=230,
        annotations=[dict(text=f"<b>{total}</b><br><span style='font-size:10px'>issues</span>",
                          x=.5, y=.5, font_size=16, font_color="#6366f1", showarrow=False)],
    )
    return fig


def _chart_top_columns(results, limit=12):
    if not results:
        return None
    top = sorted(results, key=lambda r: r.total_failures, reverse=True)[:limit]
    cmap = {"CRITICAL":"#ef4444","WARNING":"#f59e0b","INFO":"#3b82f6"}
    fig = go.Figure(go.Bar(
        x=[r.total_failures for r in top], y=[r.column_name for r in top], orientation="h",
        marker=dict(color=[cmap.get(r.severity.value,"#94a3b8") for r in top], line=dict(width=0)),
        customdata=[[r.rule_name, r.severity.value, f"{r.failure_percentage:.1f}"] for r in top],
        hovertemplate="<b>%{y}</b><br>Rule: %{customdata[0]}<br>Failures: %{x:,}<br>Rate: %{customdata[2]}%<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(99,102,241,.1)", tickfont=dict(size=11),
                   title=dict(text="Failure Count", font=dict(size=11))),
        yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
        margin=dict(t=10,b=30,l=0,r=0), height=max(220, len(top)*26),
    )
    return fig


def _chart_rule_types(results, limit=10):
    if not results:
        return None
    counts = defaultdict(int)
    for r in results:
        counts[r.rule_name] += r.total_failures
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    labels, values = zip(*top)
    fig = go.Figure(go.Bar(
        x=list(labels), y=list(values),
        marker=dict(color=list(values), colorscale=[[0,"#3b82f6"],[.5,"#8b5cf6"],[1,"#ef4444"]], line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>Total failures: %{y:,}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=11), tickangle=-30),
        yaxis=dict(gridcolor="rgba(99,102,241,.1)", tickfont=dict(size=11),
                   title=dict(text="Total Failures", font=dict(size=11))),
        margin=dict(t=10,b=60,l=0,r=0), height=260,
    )
    return fig


def _render_datadoctor(doctor, report_or_batch, is_batch: bool, form_key: str):
    """
    Shared DataDoctor widget rendered full-width below results.
    Handles: orb animation, streaming initial analysis, conversation history,
    follow-up form, LLM-switch re-analyze button.
    """
    if not st.session_state.data_doctor_enabled:
        st.info("DataDoctor disabled. Enable in sidebar settings.")
        return

    # ── Check if LLM has changed since last analysis ──────────────────────
    current_model_id = f"{doctor.backend}/{doctor.model}" if doctor else None
    last_model_id    = st.session_state.get("data_doctor_model")
    model_changed    = (
        st.session_state.data_doctor_analysis is not None
        and current_model_id is not None
        and current_model_id != last_model_id
    )

    # ── Orb header ────────────────────────────────────────────────────────
    thinking_now = (st.session_state.data_doctor_analysis is None and doctor is not None)
    if doctor:
        st.markdown(_dd_orb(doctor.backend, doctor.model, thinking=thinking_now),
                    unsafe_allow_html=True)
    else:
        st.markdown("### 🤖 DataDoctor")

    # ── LLM-switch re-analyze notice ──────────────────────────────────────
    if model_changed:
        ra_col, info_col = st.columns([2, 5])
        with info_col:
            st.info(f"Analysis was by `{last_model_id}` · current: `{current_model_id}`")
        with ra_col:
            if st.button("🔄 Re-analyze with current LLM", key=f"reanalyze_{form_key}"):
                st.session_state.data_doctor_analysis = None
                st.session_state.followup_messages    = []
                doctor.reset_conversation()
                st.rerun()

    # ── Analysis + conversation ───────────────────────────────────────────
    if st.session_state.data_doctor_analysis:
        # Initial analysis as first assistant message
        with st.chat_message("assistant"):
            st.markdown(st.session_state.data_doctor_analysis)

        # Conversation history
        for msg in st.session_state.followup_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Follow-up form — always at the bottom
        with st.form(form_key, clear_on_submit=True):
            cq, cbtn = st.columns([6, 1])
            with cq:
                question = st.text_input(
                    "q", placeholder="Ask DataDoctor a follow-up question…",
                    label_visibility="collapsed"
                )
            with cbtn:
                submitted = st.form_submit_button("Send →", use_container_width=True)

        if submitted and question and doctor:
            st.session_state.followup_messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                resp = st.write_stream(doctor.stream_followup(question))
                st.session_state.followup_messages.append({"role": "assistant", "content": resp})
            st.rerun()  # push new exchange above the form on next render

    elif doctor:
        # Stream initial analysis
        try:
            if is_batch:
                analysis = st.write_stream(doctor.stream_batch_analysis(report_or_batch))
            else:
                analysis = st.write_stream(doctor.stream_analysis(report_or_batch))
        except Exception as e:
            st.error(f"DataDoctor error: {e}")
            analysis = None
        if analysis:
            st.session_state.data_doctor_analysis = analysis
            st.session_state.data_doctor_model    = f"{doctor.backend}/{doctor.model}"
            st.rerun()
    else:
        st.info("Configure LLM backend in the sidebar.")


# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Data Quality Validator", layout="wide", page_icon="🔍")
st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)
st.markdown("""
<div class="page-title">
  <h1>🔍 Data Quality Validator</h1>
  <p>AI-Powered Enterprise Data Intelligence · Real-time validation · Conversational insights</p>
</div>
""", unsafe_allow_html=True)

# ── session state ─────────────────────────────────────────────────────────────
_DEFAULTS = {
    "db_connector": None, "validation_results": None, "batch_results": None,
    "selected_rulesets": [], "selected_issue_key": None, "rule_mapper": RuleMapper(),
    "validation_mode": "single", "available_databases": [],
    "server_tested": False, "tested_server_name": None, "tested_credentials": None,
    "data_doctor": None, "data_doctor_enabled": True,
    "data_doctor_analysis": None, "followup_messages": [],
    "data_doctor_model": None,
    "last_validation_config": None,
    "show_groq_input": False,
    "llm_backend": os.getenv("LLM_PROVIDER", "ollama"),
    "ollama_url": os.getenv("OLLAMA_API_URL", "http://localhost:11434"),
    "ollama_model": os.getenv("OLLAMA_MODEL", ""),
    "groq_model": DataDoctor.GROQ_MODELS[0],
    "groq_api_key": os.getenv("GROQ_API_KEY", ""),
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗄️ Database")
    server = st.text_input("Server", placeholder="localhost or IP", key="server_input")
    username = st.text_input("Username", placeholder="Blank = Windows Auth", key="username_input")
    password = st.text_input("Password", type="password", key="password_input")

    # Show Test Connection whenever server or credentials differ from the last successful test
    _needs_test = (
        not st.session_state.server_tested
        or st.session_state.tested_server_name != server
        or st.session_state.tested_credentials != (username, password)
    )

    if server and _needs_test:
        if st.button("🔍 Test Connection", use_container_width=True):
            try:
                tmp = SQLServerConnector(server, "master", username, password)
                if tmp.connect():
                    dbs = tmp.get_database_list()
                    tmp.disconnect()
                    st.session_state.available_databases = dbs or []
                    st.session_state.server_tested = True
                    st.session_state.tested_server_name = server
                    st.session_state.tested_credentials = (username, password)
                    st.success("✅ Server reachable")
                    st.rerun()
                else:
                    st.error("❌ Cannot reach server")
            except Exception as e:
                st.error(str(e))

    if (st.session_state.server_tested
            and st.session_state.tested_server_name == server
            and st.session_state.tested_credentials == (username, password)
            and st.session_state.available_databases):
        database = st.selectbox("Database", st.session_state.available_databases, key="database_select")
    else:
        database = st.text_input("Database", placeholder="Enter manually", key="database_input")

    if st.button("Connect", use_container_width=True):
        try:
            conn = SQLServerConnector(server, database, username, password)
            if conn.connect():
                st.session_state.db_connector = conn
                st.success("✅ Connected")
                st.rerun()
            else:
                st.error("❌ Connection failed")
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.markdown("### 🤖 DataDoctor")
    st.session_state.data_doctor_enabled = st.checkbox(
        "Enable DataDoctor AI", value=st.session_state.data_doctor_enabled
    )
    if st.session_state.data_doctor_enabled:
        backend = st.selectbox(
            "Backend", ["ollama", "groq"],
            index=0 if st.session_state.llm_backend == "ollama" else 1,
            key="llm_backend_select",
        )
        if backend != st.session_state.llm_backend:
            st.session_state.llm_backend = backend
            st.session_state.data_doctor = None

        if backend == "ollama":
            new_url = st.text_input("Ollama URL", value=st.session_state.ollama_url, key="ollama_url_input")
            if new_url != st.session_state.ollama_url:
                st.session_state.ollama_url = new_url
                st.session_state.data_doctor = None
                _fetch_ollama_models.clear()
            avail = _fetch_ollama_models(st.session_state.ollama_url)
            if avail:
                cur = st.session_state.ollama_model or avail[0]
                idx = avail.index(cur) if cur in avail else 0
                st.session_state.ollama_model = st.selectbox("Model", avail, index=idx, key="ollama_model_select")
                st.caption(f"✅ {len(avail)} model(s) · `1b` ⚡ `4b` 🔄 `7b+` 🧠")
            else:
                st.session_state.ollama_model = st.text_input(
                    "Model (manual)", value=st.session_state.ollama_model or "llama3",
                    key="ollama_model_manual"
                )
                st.warning("⚠️ Ollama unreachable — run `ollama serve`")

        else:  # groq
            gk = st.session_state.groq_api_key
            if gk and not st.session_state.show_groq_input:
                # Show masked key
                masked = f"{'•' * 20}{gk[-4:]}"
                st.markdown(
                    f'<code style="font-size:.78rem;opacity:.8">{masked}</code>',
                    unsafe_allow_html=True
                )
                if st.button("✏️ Change key", key="change_groq_key"):
                    st.session_state.show_groq_input = True
                    st.rerun()
            else:
                ek = st.text_input(
                    "Groq API Key", type="password",
                    value=st.session_state.groq_api_key, key="groq_key_input"
                )
                if ek and ek != st.session_state.groq_api_key:
                    st.session_state.groq_api_key   = ek
                    st.session_state.data_doctor     = None
                    st.session_state.show_groq_input = False
                if not gk:
                    st.caption("Add GROQ_API_KEY to .env or enter above")

            st.session_state.groq_model = st.selectbox(
                "Model", DataDoctor.GROQ_MODELS,
                index=DataDoctor.GROQ_MODELS.index(st.session_state.groq_model)
                if st.session_state.groq_model in DataDoctor.GROQ_MODELS else 0,
                key="groq_model_select",
            )
            st.caption("⚡ Free tier · ~50× faster than local · great for demos")

# ── not connected ─────────────────────────────────────────────────────────────
if not st.session_state.db_connector:
    _, _c, _ = st.columns([1, 2, 1])
    with _c:
        st.markdown("""
        <div style="text-align:center;padding:40px 0 20px 0;">
            <p style="font-size:1.05rem;opacity:.7;">No database connected yet.</p>
            <p style="font-size:.85rem;opacity:.5;">Connect via the sidebar — or explore a live demo below.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🎭  Try Live Demo — Healthcare Dataset (55,500 rows)",
                     use_container_width=True, key="demo_btn"):
            from demo_data import get_demo_report
            st.session_state.validation_results = get_demo_report()
            st.session_state.batch_results = None
            st.session_state.selected_issue_key = None
            st.session_state.data_doctor_analysis = None
            st.session_state.followup_messages = []
            st.session_state.last_validation_config = {
                "mode": "single",
                "table": "dbo.PatientRecords",
                "rulesets": ["healthcare_records_rules.json"],
                "schema": {
                    "Name": "nvarchar", "Age": "int", "Gender": "nvarchar",
                    "BloodType": "nvarchar", "MedicalCondition": "nvarchar",
                    "DateOfAdmission": "date", "Doctor": "nvarchar",
                    "Hospital": "nvarchar", "InsuranceProvider": "nvarchar",
                    "BillingAmount": "decimal", "RoomNumber": "int",
                    "AdmissionType": "nvarchar", "DischargeDate": "date",
                    "Medication": "nvarchar", "TestResults": "nvarchar"
                },
                "sn": "dbo", "tn": "PatientRecords",
            }
            st.rerun()
        st.caption("🐳 Run `docker compose up` locally to connect your own SQL Server database.")
    st.stop()

st.markdown(
    '<span style="color:#10b981;font-size:.8rem;">●</span>'
    ' <span style="font-size:.82rem;opacity:.6;">Database connected</span>',
    unsafe_allow_html=True,
)
st.markdown("")

rule_loader = RuleLoader()
all_tables  = st.session_state.db_connector.get_tables()

# ══════════════════════════════════════════════════════════════════════════════
# SETUP PANEL  (hidden once results are showing)
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.validation_results and not st.session_state.batch_results:

    with st.expander("⚙️ Validation Setup", expanded=True):
        c1, c2, c3 = st.columns([1, 2, 2])
        with c1:
            mode_label = st.radio("Mode", ["Single Table", "Batch"], key="mode_select")
            st.session_state.validation_mode = "batch" if mode_label == "Batch" else "single"

        if st.session_state.validation_mode == "single":
            with c2:
                selected_table = st.selectbox("Table", all_tables, key="table_select")
                sn = selected_table.split(".")[0] if "." in selected_table else "dbo"
                tn = selected_table.split(".")[1] if "." in selected_table else selected_table
                table_schema = st.session_state.db_connector.get_table_schema(sn, tn)
                suggested    = rule_loader.suggest_rulesets_for_schema(table_schema)
            with c3:
                all_rulesets     = rule_loader.get_available_rulesets()
                selected_rulesets = st.multiselect(
                    "Rulesets", options=all_rulesets, default=suggested,
                    key="ruleset_select", help="Auto-suggested from column data types",
                )
        else:
            with c2:
                selected_batch_tables = st.multiselect(
                    "Tables", options=all_tables,
                    default=[all_tables[0]] if all_tables else [],
                    key="batch_table_select",
                )
            with c3:
                all_rulesets      = rule_loader.get_available_rulesets()
                selected_rulesets = st.multiselect("Rulesets", options=all_rulesets, key="ruleset_select_batch")

    # ── Rule mapper ──────────────────────────────────────────────────────────
    if st.session_state.validation_mode == "single":
        if selected_rulesets:
            rule_loader.load_multiple_rulesets(selected_rulesets)
            all_rules  = rule_loader.get_engine().get_all_rules()
            avail_cols = list(table_schema.keys())
            with st.expander(
                f"🗺️ Rule → Column Mapping  ·  {len(all_rules)} rule(s)  ·  {len(avail_cols)} column(s)",
                expanded=False,
            ):
                st.caption("Map each rule to the columns it should check. NULL/blank checks always run on all columns.")
                st.session_state.rule_mapper.clear_mappings()
                for rule in all_rules:
                    cr, cc = st.columns([2, 3])
                    with cr:
                        st.markdown(
                            f'<span class="chip-{rule.severity.value.lower()}">{rule.severity.value}</span>&nbsp; **{rule.rule_name}**',
                            unsafe_allow_html=True)
                        st.caption(rule.rule_description)
                    with cc:
                        mapped = st.multiselect("cols", options=avail_cols, key=f"mapper_{rule.rule_id}",
                                                placeholder="Select columns…", label_visibility="collapsed")
                        if mapped:
                            st.session_state.rule_mapper.add_mapping(rule.rule_id, mapped)

        cb, _ = st.columns([2, 5])
        with cb:
            run_single = st.button("▶  Run Validation", key="validate_btn_single", use_container_width=True)
        if run_single:
            if selected_rulesets and not st.session_state.rule_mapper.get_all_mappings():
                st.error("❌ Map at least one rule to a column first.")
            else:
                with st.spinner("Validating…"):
                    try:
                        rl = RuleLoader()
                        if selected_rulesets:
                            rl.load_multiple_rulesets(selected_rulesets)
                        engine = ValidationEngine(st.session_state.db_connector, rl)
                        engine.set_rule_mapper(st.session_state.rule_mapper)
                        report = engine.validate_table(selected_table, selected_rulesets=selected_rulesets)
                        st.session_state.validation_results = report
                        st.session_state.batch_results      = None
                        st.session_state.selected_issue_key = None
                        st.session_state.data_doctor_analysis = None
                        st.session_state.followup_messages    = []
                        st.session_state.data_doctor_model    = None
                        st.session_state.last_validation_config = {
                            "mode": "single", "table": selected_table,
                            "rulesets": selected_rulesets, "schema": table_schema,
                            "sn": sn, "tn": tn,
                        }
                        if st.session_state.data_doctor_enabled:
                            doc = _ensure_data_doctor()
                            if doc:
                                doc.reset_conversation()
                        st.success("✅ Done!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")

    else:  # batch setup
        if selected_batch_tables and selected_rulesets:
            all_cols = sorted(set(
                col for tbl in selected_batch_tables
                for col in st.session_state.db_connector.get_table_schema(
                    tbl.split(".")[0] if "." in tbl else "dbo",
                    tbl.split(".")[1] if "." in tbl else tbl
                ).keys()
            ))
            rule_loader.load_multiple_rulesets(selected_rulesets)
            all_rules = rule_loader.get_engine().get_all_rules()
            with st.expander(
                f"🗺️ Rule → Column Mapping  ·  {len(all_rules)} rule(s)  ·  across {len(selected_batch_tables)} table(s)",
                expanded=False,
            ):
                st.caption("Columns that don't exist in a table are automatically skipped.")
                st.session_state.rule_mapper.clear_mappings()
                for rule in all_rules:
                    cr, cc = st.columns([2, 3])
                    with cr:
                        st.markdown(
                            f'<span class="chip-{rule.severity.value.lower()}">{rule.severity.value}</span>&nbsp; **{rule.rule_name}**',
                            unsafe_allow_html=True)
                        st.caption(rule.rule_description)
                    with cc:
                        mapped = st.multiselect("cols", options=all_cols, key=f"mapper_batch_{rule.rule_id}",
                                                placeholder="Select columns…", label_visibility="collapsed")
                        if mapped:
                            st.session_state.rule_mapper.add_mapping(rule.rule_id, mapped)

        if selected_batch_tables:
            cb, _ = st.columns([2, 5])
            with cb:
                run_batch = st.button("▶  Run Batch Validation", key="validate_btn_batch", use_container_width=True)
            if run_batch:
                if selected_rulesets and not st.session_state.rule_mapper.get_all_mappings():
                    st.error("❌ Map at least one rule to a column first.")
                else:
                    prog = st.progress(0); prog_txt = st.empty()
                    try:
                        rl = RuleLoader()
                        if selected_rulesets:
                            rl.load_multiple_rulesets(selected_rulesets)
                        bv = BatchValidator(st.session_state.db_connector, rl)
                        bv.engine.set_rule_mapper(st.session_state.rule_mapper)
                        def _cb(cur, tot, tbl):
                            prog.progress(cur / tot); prog_txt.text(f"Validating {cur}/{tot}: {tbl}")
                        batch_report = bv.validate_multiple_tables(
                            selected_batch_tables, selected_rulesets=selected_rulesets, progress_callback=_cb)
                        st.session_state.batch_results      = batch_report
                        st.session_state.validation_results = None
                        st.session_state.selected_issue_key = None
                        st.session_state.data_doctor_analysis = None
                        st.session_state.followup_messages    = []
                        st.session_state.data_doctor_model    = None
                        st.session_state.last_validation_config = {
                            "mode": "batch", "tables": selected_batch_tables,
                            "rulesets": selected_rulesets,
                        }
                        if st.session_state.data_doctor_enabled:
                            doc = _ensure_data_doctor()
                            if doc:
                                doc.reset_conversation()
                        st.success("✅ Batch validation complete!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SINGLE TABLE RESULTS
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.validation_results and not st.session_state.batch_results:
    report = st.session_state.validation_results

    # compact header
    cb, ci, cdl = st.columns([1, 5, 2])
    with cb:
        if st.button("← Back", key="back_single"):
            st.session_state.validation_results  = None
            st.session_state.data_doctor_analysis = None
            st.session_state.followup_messages    = []
            st.session_state.data_doctor_model    = None
            st.rerun()
    with ci:
        st.markdown(
            f"**{report.table_name}**"
            f"<span style='opacity:.6'> &nbsp;·&nbsp; {report.total_rows_checked:,} rows &nbsp;·&nbsp; {len(report.results)} issue(s)</span>",
            unsafe_allow_html=True)
    with cdl:
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("📥 CSV",
                ExportManager.export_table_report_to_csv(report),
                file_name=f"{report.table_name.replace('.','_')}_report.csv",
                mime="text/csv", use_container_width=True)
        with d2:
            st.download_button("📥 Excel",
                ExportManager.export_table_report_to_excel(report),
                file_name=f"{report.table_name.replace('.','_')}_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

    st.divider()

    # scorecards
    crit_r = [r for r in report.results if r.severity.value == "CRITICAL"]
    warn_r = [r for r in report.results if r.severity.value == "WARNING"]
    info_r = [r for r in report.results if r.severity.value == "INFO"]
    health = max(0.0, 100 - sum(r.total_failures for r in report.results) / max(report.total_rows_checked, 1) * 100)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Rows",   f"{report.total_rows_checked:,}")
    m2.metric("Issues Found", len(report.results))
    m3.metric("🔴 Critical",  len(crit_r))
    m4.metric("🟡 Warning",   len(warn_r))
    m5.metric("Health Score", f"{health:.1f}%",
        delta="Good" if health >= 90 else ("Fair" if health >= 70 else "Poor"),
        delta_color="normal" if health >= 90 else ("off" if health >= 70 else "inverse"))

    st.divider()

    if report.results:
        ch1, ch2, ch3 = st.columns([1, 2, 2])
        with ch1:
            st.markdown("**Severity Split**")
            f = _chart_severity(len(crit_r), len(warn_r), len(info_r))
            if f: st.plotly_chart(f, use_container_width=True, config={"displayModeBar": False})
        with ch2:
            st.markdown("**Top Failing Columns**")
            f2 = _chart_top_columns(report.results)
            if f2: st.plotly_chart(f2, use_container_width=True, config={"displayModeBar": False})
        with ch3:
            st.markdown("**Failures by Rule Type**")
            f3 = _chart_rule_types(report.results)
            if f3: st.plotly_chart(f3, use_container_width=True, config={"displayModeBar": False})

        st.divider()

        col_list, col_detail = st.columns([1.5, 1.5])
        with col_list:
            st.markdown("#### Issues  *(click to inspect)*")
            for sev_lbl, sev_set in [("🔴 CRITICAL",crit_r),("🟡 WARNING",warn_r),("🔵 INFO",info_r)]:
                if sev_set:
                    st.markdown(f"**{sev_lbl}**")
                    for i, r in enumerate(sev_set):
                        k = f"{sev_lbl.split()[1].lower()}_{i}_{r.rule_name}_{r.column_name}"
                        if st.button(
                            f"{r.rule_name}  ·  `{r.column_name}`  ·  {r.total_failures:,} failures ({r.failure_percentage:.1f}%)",
                            key=k, use_container_width=True
                        ):
                            st.session_state.selected_issue_key = k

        with col_detail:
            st.markdown("#### Drill-Down")
            if st.session_state.selected_issue_key:
                sel = next(
                    (r for r in report.results
                     if r.rule_name in st.session_state.selected_issue_key
                     and r.column_name in st.session_state.selected_issue_key),
                    None
                )
                if sel:
                    sv = sel.severity.value
                    st.markdown(f'<span class="chip-{sv.lower()}">{sv}</span>&nbsp; **{sel.rule_name}**', unsafe_allow_html=True)
                    st.markdown(f"Column: `{sel.column_name}`")
                    st.markdown(f"**{sel.total_failures:,}** failures ({sel.failure_percentage:.2f}%)")
                    if sel.failures:
                        expected = _friendly_expected(sel.failures[0].rule_violated)
                        st.markdown(f"Expected: *{expected}*")
                        st.markdown(f"*Up to 10 sample rows:*")
                        st.dataframe(
                            [{"Row": f.row_id,
                              "Actual Value": str(f.actual_value)[:80] if f.actual_value else "NULL",
                              "Expected":     expected}
                             for f in sel.failures[:10]],
                            use_container_width=True, hide_index=True)
                    else:
                        st.caption("No sample rows captured.")
                else:
                    st.caption("Click an issue on the left to inspect.")
            else:
                st.caption("← Click an issue to inspect sample failing rows.")
    else:
        st.success("✅ No issues found — data quality is excellent!")

    # ── Re-validate / Update Mappings ─────────────────────────────────────
    cfg = st.session_state.get("last_validation_config")
    if cfg and cfg.get("mode") == "single":
        with st.expander("⚙️ Re-validate / Update Column Mappings", expanded=False):
            st.caption(f"Table: **{cfg['table']}** · Rulesets: {', '.join(cfg['rulesets']) if cfg['rulesets'] else 'none (standard checks only)'}")
            avail_cols = list(cfg["schema"].keys())

            if cfg["rulesets"]:
                rl_tmp = RuleLoader()
                rl_tmp.load_multiple_rulesets(cfg["rulesets"])
                rules_tmp = rl_tmp.get_engine().get_all_rules()
                new_mapper = RuleMapper()
                st.markdown("**Update column mappings if needed:**")
                for rule in rules_tmp:
                    cr2, cc2 = st.columns([2, 3])
                    with cr2:
                        st.markdown(
                            f'<span class="chip-{rule.severity.value.lower()}">{rule.severity.value}</span>&nbsp; **{rule.rule_name}**',
                            unsafe_allow_html=True)
                    with cc2:
                        cur_mapping = st.session_state.rule_mapper.get_mapped_columns(rule.rule_id)
                        new_mapped = st.multiselect(
                            "cols", options=avail_cols,
                            default=[c for c in cur_mapping if c in avail_cols],
                            key=f"revalidate_mapper_{rule.rule_id}",
                            placeholder="Select columns…", label_visibility="collapsed",
                        )
                        if new_mapped:
                            new_mapper.add_mapping(rule.rule_id, new_mapped)
            else:
                new_mapper = RuleMapper()

            if st.button("▶  Re-validate Now", key="revalidate_btn", use_container_width=False):
                with st.spinner("Re-validating…"):
                    try:
                        rl2 = RuleLoader()
                        if cfg["rulesets"]:
                            rl2.load_multiple_rulesets(cfg["rulesets"])
                        eng2 = ValidationEngine(st.session_state.db_connector, rl2)
                        eng2.set_rule_mapper(new_mapper)
                        new_report = eng2.validate_table(cfg["table"], selected_rulesets=cfg["rulesets"])
                        st.session_state.validation_results  = new_report
                        st.session_state.rule_mapper         = new_mapper
                        st.session_state.data_doctor_analysis = None
                        st.session_state.followup_messages    = []
                        st.session_state.data_doctor_model    = None
                        st.session_state.last_validation_config["schema"] = cfg["schema"]
                        doc = _ensure_data_doctor()
                        if doc:
                            doc.reset_conversation()
                        st.success("✅ Re-validation complete!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")

    # ── DataDoctor ────────────────────────────────────────────────────────
    if st.session_state.data_doctor_enabled:
        st.divider()
        doctor = _ensure_data_doctor()
        _render_datadoctor(doctor, report, is_batch=False, form_key="followup_form_single")


# ══════════════════════════════════════════════════════════════════════════════
# BATCH RESULTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.batch_results:
    batch_report = st.session_state.batch_results

    cb, ci, cdl = st.columns([1, 5, 2])
    with cb:
        if st.button("← Back", key="back_batch"):
            st.session_state.batch_results       = None
            st.session_state.data_doctor_analysis = None
            st.session_state.followup_messages    = []
            st.session_state.data_doctor_model    = None
            st.rerun()
    with ci:
        st.markdown(
            f"**Batch Report**"
            f"<span style='opacity:.6'> &nbsp;·&nbsp; {batch_report.total_tables} table(s) &nbsp;·&nbsp; {batch_report.total_issues} issue(s)</span>",
            unsafe_allow_html=True)
    with cdl:
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("📥 CSV",
                ExportManager.export_batch_report_to_csv(batch_report),
                file_name="batch_report.csv", mime="text/csv", use_container_width=True)
        with d2:
            st.download_button("📥 Excel",
                ExportManager.export_batch_report_to_excel(batch_report),
                file_name="batch_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

    st.divider()

    bm1, bm2, bm3, bm4 = st.columns(4)
    bm1.metric("Tables Validated", batch_report.total_tables)
    bm2.metric("Total Issues",     batch_report.total_issues)
    bm3.metric("🔴 Critical",      batch_report.get_critical_count())
    bm4.metric("🟡 Warning",       batch_report.get_warning_count())

    all_r = [r for tr in batch_report.table_reports for r in tr.results]
    if all_r:
        st.divider()
        bc1, bc2, bc3 = st.columns([1, 2, 2])
        with bc1:
            st.markdown("**Severity Split**")
            f = _chart_severity(batch_report.get_critical_count(), batch_report.get_warning_count(), batch_report.get_info_count())
            if f: st.plotly_chart(f, use_container_width=True, config={"displayModeBar": False})
        with bc2:
            st.markdown("**Top Failing Columns**")
            f2 = _chart_top_columns(all_r)
            if f2: st.plotly_chart(f2, use_container_width=True, config={"displayModeBar": False})
        with bc3:
            st.markdown("**Failures by Rule Type**")
            f3 = _chart_rule_types(all_r)
            if f3: st.plotly_chart(f3, use_container_width=True, config={"displayModeBar": False})

    st.divider()
    st.markdown("### Results by Table")

    for t_idx, t_report in enumerate(batch_report.table_reports):
        n      = len(t_report.results)
        crit_n = sum(1 for r in t_report.results if r.severity.value == "CRITICAL")
        icon   = "🔴" if crit_n else ("🟡" if n else "✅")
        with st.expander(f"{icon} {t_report.table_name}  ·  {n} issue(s)  ·  {t_report.total_rows_checked:,} rows", expanded=crit_n > 0):
            if not t_report.results:
                st.success("No issues found"); continue
            tm1, tm2, tm3 = st.columns(3)
            tm1.metric("Rows",     f"{t_report.total_rows_checked:,}")
            tm2.metric("Issues",   n)
            tm3.metric("Critical", crit_n)
            st.divider()
            ci2, cd2 = st.columns([1.5, 1.5])
            with ci2:
                st.markdown("**Issues *(click to inspect)***")
                for sev_lbl, sev_filter in [("🔴 CRITICAL","CRITICAL"),("🟡 WARNING","WARNING"),("🔵 INFO","INFO")]:
                    sev_r = [r for r in t_report.results if r.severity.value == sev_filter]
                    if sev_r:
                        st.markdown(f"**{sev_lbl}**")
                        for i2, r in enumerate(sev_r):
                            ik = f"b_{t_idx}_{sev_filter.lower()}_{i2}_{r.rule_name}_{r.column_name}"
                            if st.button(f"{r.rule_name}  ·  `{r.column_name}`  ·  {r.total_failures:,}",
                                         key=ik, use_container_width=True):
                                st.session_state.selected_issue_key = f"{t_idx}_{r.rule_name}_{r.column_name}"
            with cd2:
                st.markdown("**Drill-Down**")
                if st.session_state.selected_issue_key:
                    parts = st.session_state.selected_issue_key.split("_", 1)
                    if parts[0].isdigit() and int(parts[0]) == t_idx:
                        for r in t_report.results:
                            if (r.rule_name in st.session_state.selected_issue_key
                                    and r.column_name in st.session_state.selected_issue_key):
                                sv = r.severity.value
                                st.markdown(f'<span class="chip-{sv.lower()}">{sv}</span>&nbsp; **{r.rule_name}** · `{r.column_name}`', unsafe_allow_html=True)
                                st.markdown(f"**{r.total_failures:,}** failures ({r.failure_percentage:.2f}%)")
                                if r.failures:
                                    expected = _friendly_expected(r.failures[0].rule_violated)
                                    st.markdown(f"Expected: *{expected}*")
                                    st.dataframe(
                                        [{"Row": f.row_id,
                                          "Actual Value": str(f.actual_value)[:80] if f.actual_value else "NULL",
                                          "Expected":     expected}
                                         for f in r.failures[:10]],
                                        use_container_width=True, hide_index=True)
                                else:
                                    st.caption("No sample rows captured.")
                                break
                else:
                    st.caption("← Click an issue.")

    # ── Re-validate (batch) ───────────────────────────────────────────────
    cfg = st.session_state.get("last_validation_config")
    if cfg and cfg.get("mode") == "batch":
        with st.expander("⚙️ Re-validate / Update Batch Settings", expanded=False):
            st.caption(f"Tables: {', '.join(cfg.get('tables', []))}  ·  Rulesets: {', '.join(cfg.get('rulesets', []))}")
            if st.button("▶  Re-run Batch Validation", key="revalidate_batch_btn"):
                with st.spinner("Re-validating…"):
                    try:
                        rl2 = RuleLoader()
                        if cfg["rulesets"]:
                            rl2.load_multiple_rulesets(cfg["rulesets"])
                        bv2 = BatchValidator(st.session_state.db_connector, rl2)
                        bv2.engine.set_rule_mapper(st.session_state.rule_mapper)
                        def _cb2(cur, tot, tbl):
                            pass
                        new_batch = bv2.validate_multiple_tables(
                            cfg["tables"], selected_rulesets=cfg["rulesets"], progress_callback=_cb2)
                        st.session_state.batch_results       = new_batch
                        st.session_state.data_doctor_analysis = None
                        st.session_state.followup_messages    = []
                        st.session_state.data_doctor_model    = None
                        doc = _ensure_data_doctor()
                        if doc:
                            doc.reset_conversation()
                        st.success("✅ Re-validation complete!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")

    # ── DataDoctor ────────────────────────────────────────────────────────
    if st.session_state.data_doctor_enabled:
        st.divider()
        doctor = _ensure_data_doctor()
        _render_datadoctor(doctor, batch_report, is_batch=True, form_key="followup_form_batch")
