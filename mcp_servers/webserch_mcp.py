import os
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Initialize FastMCP for the WebSearch Server
mcp = FastMCP("WebSearch Server")

# Initialize Tavily Client using the API Key from .env
import streamlit as st

def get_secret(key):
    try:
        return os.getenv(key) or st.secrets[key]
    except Exception:
        return os.getenv(key)

TAVILY_API_KEY = get_secret("TAVILY_API_KEY")

if not TAVILY_API_KEY:
    # Do NOT crash the app in cloud
    tavily = None
else:
    tavily = TavilyClient(api_key=TAVILY_API_KEY)


def _execute_clinical_search(query: str, max_results: int = 5) -> dict:
    """
    Standardized internal helper to execute Tavily searches and 
    format results for clinical accuracy.
    """
    if not tavily:
        return {"error": "TAVILY_API_KEY missing"}
    try:
        response = tavily.search(query=query, max_results=max_results, search_depth="advanced")
        results = [
            {
                "title": r.get("title", "No Title"),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:800] # Truncated to stay within token limits
            }
            for r in response.get("results", [])
        ]
        return {
            "search_query": query,
            "total_matches": len(results),
            "results": results
        }
    except Exception as e:
        return {"error": f"Tavily Search Error: {str(e)}"}

# ── Tool 1: General Clinical Web Search ──────────────────────────────────────
@mcp.tool()
def web_search(query: str, max_results: int = 5) -> dict:
    """
    General web search for any clinical trial related query.
    Use this as a fallback for general questions, disease information, or company news.
    """
    return _execute_clinical_search(query, max_results)

# ── Tool 2: CDISC Guidelines Search ──────────────────────────────────────────
@mcp.tool()
def search_cdisc_guidelines(topic: str) -> dict:
    """
    Search for CDISC SDTM standards, column names, and controlled terminology.
    Use this when the user asks about SDTM mapping, domain variables, or compliance rules.
    Example topics: 'AE domain variables', 'AESEV controlled terminology'
    """
    # Boosting the query with specific CDISC context
    clinical_query = f"CDISC SDTM implementation guide {topic} controlled terminology standards"
    return _execute_clinical_search(clinical_query, max_results=4)

# ── Tool 3: FDA Regulatory Search ────────────────────────────────────────────
@mcp.tool()
def search_fda_guidelines(topic: str) -> dict:
    """
    Search FDA guidance documents, SAE reporting rules, and 21 CFR regulations.
    Use this when the user asks about regulatory submissions, safety reporting timelines, or FDA requirements.
    Example topics: 'SAE reporting timeline', 'electronic submission requirements'
    """
    clinical_query = f"FDA official guidance {topic} 21 CFR clinical trial regulation"
    return _execute_clinical_search(clinical_query, max_results=4)

# ── Tool 4: Drug Information Search ──────────────────────────────────────────
@mcp.tool()
def search_drug_info(drug_name: str) -> dict:
    """
    Search for drug interactions, mechanism of action, and known side effects.
    Use this for the Concomitant Medications (CM) domain or checking known side effects.
    Example: 'Metformin interactions', 'Lisinopril known side effects'
    """
    clinical_query = f"{drug_name} mechanism of action pharmacology side effects clinical trials"
    return _execute_clinical_search(clinical_query, max_results=4)

# ── Tool 5: Adverse Event Medical Search ─────────────────────────────────────
@mcp.tool()
def search_adverse_event_info(event_term: str) -> dict:
    """
    Search for medical information about an adverse event or condition.
    Use this to understand severity, clinical management, or CTCAE grading.
    Example: 'hepatotoxicity grading', 'cardiac arrest clinical significance'
    """
    clinical_query = f"{event_term} clinical management CTCAE grading adverse event significance"
    return _execute_clinical_search(clinical_query, max_results=4)

# ── Tool 6: Clinical Trial Protocol Standards Search ─────────────────────────
@mcp.tool()
def search_protocol_standards(topic: str) -> dict:
    """
    Search ICH GCP guidelines and international protocol design standards.
    Use this for GCP rules, dose reduction standards, and informed consent guidelines.
    Example: 'ICH E6 GCP informed consent', 'dose reduction rules clinical trial'
    """
    clinical_query = f"ICH E6 GCP protocol standard {topic} clinical trial guidelines"
    return _execute_clinical_search(clinical_query, max_results=4)

if __name__ == "__main__":
    # Start the server using Stdio transport for local execution
    mcp.run(transport="stdio")