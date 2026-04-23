import streamlit as st
import json
import os
import re
from groq import Groq
from dotenv import load_dotenv

# ── 1. CORE INTEGRATIONS ──────────────────────────────────────────────────────
# MCP Client and Local Functions
from mcp_client.client import call_tool
from tools.query_sdtm import query_sdtm
from tools.validate_domain import validate_domain
from tools.summarize_patient import summarize_patient
from tools.flag_safety_signals import flag_safety_signals

# Force reload environment variables
load_dotenv()

# ── 2. PAGE CONFIG & ATTRACTIVE UI ───────────────────────────────────────────
st.set_page_config(
    page_title="ClinIQ — Clinical Trial Data Assistant",
    page_icon="🧬",
    layout="wide"
)

# Professional UI: Custom alignment and medical theme
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    
    /* Global Chat Message Styling */
    .stChatMessage { border-radius: 12px; border: 1px solid #30363d; margin-bottom: 12px; max-width: 80%; }
    
    /* User: Align Right with green accent */
    [data-testid="stChatMessageUser"] {
        margin-left: auto;
        background-color: #161b22;
        border-right: 4px solid #238636;
    }

    /* Assistant: Align Left with blue accent */
    [data-testid="stChatMessageAssistant"] {
        margin-right: auto;
        background-color: #0d1117;
        border-left: 4px solid #1f6feb;
    }

    .stButton>button { border-radius: 8px; font-weight: 600; height: 3em; background-color: #238636; color: white; border: none; }
    .stCaption { color: #8b949e; font-size: 0.8rem; }
    .stCode { border-radius: 10px; background-color: #161b22; }
</style>
""", unsafe_allow_html=True)

# Auth & Model Strategy
def get_secret(key):
    value = os.getenv(key)
    if value:
        return value
    try:
        return st.secrets[key]
    except Exception:
        return None

GROQ_API_KEY = get_secret("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("🔴 GROQ_API_KEY missing in environment or Streamlit secrets.")
    st.stop()

groq_client = Groq(api_key=GROQ_API_KEY.strip())
# Using llama-3.3 for high-accuracy reasoning
PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"

# ── 3. REFINED SYSTEM PROMPT ──────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are ClinIQ, a professional and highly accurate Clinical Trial Data Assistant.

MISSION:
- Help researchers analyze SDTM datasets (AE, DM, LB, CM, VS) and retrieve trial documentation.
- Searching for Clinical Protocols, SOPs, and Trial Data in Google Drive or Notion is a primary healthcare task.

NOTION PROTOCOL:
- Use 'search_notion' first to find IDs before reading a specific page.

COMMUNICATION:
- Use professional clinical language. Provide clear, data-driven summaries.
- NEVER show raw technical tags like <function> to the user.
"""

# ── 4. COMPLETE AGENTIC TOOLBOX ───────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_sdtm",
            "description": "Query local SDTM datasets (AE, DM, LB, CM, VS). Filter by age_gt, sex, or clinical variables.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "enum": ["AE", "DM", "LB", "CM", "VS"]},
                    "age_gt": {"type": "integer"},
                    "sex": {"type": "string", "enum": ["M", "F"]},
                    "filter_field": {"type": "string"},
                    "filter_value": {"type": "string"}
                },
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_patient",
            "description": "Summarize demographics and clinical history for a USUBJID.",
            "parameters": {
                "type": "object",
                "properties": {"patient_id": {"type": "string"}},
                "required": ["patient_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_domain",
            "description": "Check a domain dataset for compliance issues.",
            "parameters": {
                "type": "object",
                "properties": {"domain": {"type": "string", "enum": ["AE", "DM", "LB", "CM", "VS"]}},
                "required": ["domain"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "flag_safety_signals",
            "description": "Scan AE data for critical safety signals.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notion_tool",
            "description": "Search or read clinical SOPs in Notion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": ["search_notion", "read_notion_page"]},
                    "query": {"type": "string"},
                    "page_id": {"type": "string"}
                },
                "required": ["tool"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gdrive_tool",
            "description": "Search or read files on Google Drive.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": ["list_drive_files", "read_drive_file", "search_drive_files"]},
                    "query": {"type": "string"},
                    "keyword": {"type": "string"},
                    "file_id": {"type": "string"}
                },
                "required": ["tool"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "filesystem_tool",
            "description": "Interact with local trial folders (sdtm/documents).",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": ["list_directory", "read_file", "search_files"]},
                    "path": {"type": "string", "default": "."},
                    "filename": {"type": "string"},
                    "keyword": {"type": "string"}
                },
                "required": ["tool"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_tool",
            "description": "Search FDA/CDISC regulations or medical info online.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": ["web_search", "search_cdisc_guidelines", "search_fda_guidelines", "search_drug_info"]},
                    "query": {"type": "string"},
                    "topic": {"type": "string"},
                    "drug_name": {"type": "string"}
                },
                "required": ["tool"]
            }
        }
    }
]

# ── 5. SESSION STATE ──────────────────────────────────────────────────────────
if "messages" not in st.session_state: st.session_state.messages = []
if "history" not in st.session_state: st.session_state.history = []

# ── 6. SIDEBAR: ACTIONS & CONTEXT ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://www.ailens.ai/assets/logomain.svg", width=140)
    st.markdown("### 🧬 ClinIQ Assistant")
    st.success("📁 FS · 🌐 Web · 💾 Drive · 📝 Notion")
    st.divider()

    st.markdown("### ⚡ Quick Actions")
    if st.button("⚠️ Flag Safety Signals", use_container_width=True):
        res = flag_safety_signals()
        st.session_state.messages.append({"role": "assistant", "content": f"### 🛡️ Safety Alert\n{res.get('alert')}", "source": "flag_safety_signals"})
        st.rerun()

    if st.button("✅ Validate AE Domain", use_container_width=True):
        res = validate_domain("AE")
        st.session_state.messages.append({"role": "assistant", "content": f"### 📋 AE Validation\nStatus: {res.get('compliance_status')}", "source": "validate_domain"})
        st.rerun()

    if st.button("📁 List Data Folders", use_container_width=True):
        res = call_tool("filesystem", "list_directory", {"path": "."})
        msg = "### 📂 Project Structure\n"
        for d in res.get("directories", []):
            msg += f"- 📁 **{d}/**\n"
            sub = call_tool("filesystem", "list_directory", {"path": d})
            for f in sub.get("files", []): msg += f"  - 📄 {f}\n"
        st.session_state.messages.append({"role": "assistant", "content": msg, "source": "filesystem_tool"})
        st.rerun()

    st.divider()
    st.markdown("### 📂 Folder View")
    t_path = get_secret("TRIAL_DATA_PATH") or "./trial_data"
    for s in ["sdtm", "documents"]:
        full = os.path.join(t_path, s)
        if os.path.exists(full):
            st.caption(f"**{s.upper()}/ **")
            for f in sorted(os.listdir(full)): st.markdown(f"<small>📄 {f}</small>", unsafe_allow_html=True)

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []; st.session_state.history = []; st.rerun()

# ── 7. AGENTIC BRAIN LOOP ─────────────────────────────────────────────────────
def handle_prompt(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.history.append({"role": "user", "content": prompt})

    with st.spinner("🤖 Orchestrating sources..."):
        active_model = PRIMARY_MODEL
        try:
            # Pass 1: Tool Decision
            try:
                response = groq_client.chat.completions.create(
                    model=active_model,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.history[-6:],
                    tools=TOOLS, tool_choice="auto"
                )
            except Exception as e:
                if any(err in str(e) for err in ["429", "404", "400"]):
                    active_model = FALLBACK_MODEL
                    response = groq_client.chat.completions.create(
                        model=active_model,
                        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.history[-6:],
                        tools=TOOLS, tool_choice="auto"
                    )
                else: raise e
            
            resp_msg = response.choices[0].message
            actions_taken = []
            
            if resp_msg.tool_calls:
                st.session_state.history.append(resp_msg)
                for tool_call in resp_msg.tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    result = {"error": "Execution failed"}
                    actions_taken.append(name)

                    # 🛡️ PARAMETER GUARD: Clean hallucinated or malformed arguments
                    if name == "query_sdtm":
                        # Cast age_gt to int and strip 'severity'
                        if "age_gt" in args: args["age_gt"] = int(args["age_gt"])
                        clean = {k: v for k, v in args.items() if k in ["domain", "age_gt", "sex", "filter_field", "filter_value"]}
                        result = query_sdtm(**clean)
                    elif name == "summarize_patient": result = summarize_patient(args.get("patient_id"))
                    elif name == "validate_domain": result = validate_domain(args.get("domain"))
                    elif name == "flag_safety_signals": result = flag_safety_signals()
                    elif name == "notion_tool":
                        if "keyword" in args: args["query"] = args.pop("keyword")
                        result = call_tool("notion", args.pop("tool"), args)
                    elif name == "gdrive_tool":
                        if "query" in args and args.get("tool") == "search_drive_files": args["keyword"] = args.pop("query")
                        result = call_tool("gdrive", args.pop("tool"), args)
                    elif name == "filesystem_tool": result = call_tool("filesystem", args.pop("tool"), args)
                    elif name == "web_search_tool":
                        tool_action = args.pop("tool")
                        q_val = args.get("query") or args.get("topic") or args.get("drug_name")
                        result = call_tool("websearch", tool_action, {"query": q_val, "topic": q_val})

                    st.session_state.history.append({"role": "tool", "tool_call_id": tool_call.id, "name": name, "content": json.dumps(result)})

                # Pass 2: Final Summary
                final_res = groq_client.chat.completions.create(
                    model=active_model,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.history[-10:]
                )
                reply = final_res.choices[0].message.content
            else:
                reply = resp_msg.content

            st.session_state.messages.append({"role": "assistant", "content": reply, "source": " · ".join(actions_taken) if actions_taken else f"Groq ({active_model})"})
            st.session_state.history.append({"role": "assistant", "content": reply})

        except Exception as e:
            st.error(f"⚠️ Orchestration Error: {str(e)}")

# ── 8. UI RENDER ─────────────────────────────────────────────────────────────
st.title("🧬 ClinIQ — Clinical Trial Data Assistant")
st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("source"): st.caption(f"🔧 Source: {msg['source']}")

if prompt := st.chat_input("Ask about safety, CDISC rules, or protocol files..."):
    handle_prompt(prompt); st.rerun()