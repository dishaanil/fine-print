import json
import os
import re
import time

import requests
import streamlit as st
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────
GRAPHN_URL = os.getenv("GRAPHN_URL", "https://cp.graphn.ai")
GRAPHN_API_KEY = os.getenv("GRAPHN_API_KEY", "")
GRAPHN_WORKSPACE = os.getenv("GRAPHN_WORKSPACE", "")
WORKFLOW_ID = os.getenv("GRAPHN_WORKFLOW_ID", "wf_e382a5e427d5")

HEADERS = {
    "Authorization": f"Bearer {GRAPHN_API_KEY}",
    "X-Workspace-ID": GRAPHN_WORKSPACE,
    "Content-Type": "application/json",
}

MAX_TEXT_CHARS = 40_000  # ~10k tokens, well within 131k context

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fine Print",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .main { max-width: 900px; margin: 0 auto; }
    .risk-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 8px;
    }
    .score-ring {
        font-size: 3.5rem;
        font-weight: 900;
        line-height: 1;
    }
    .flag-card {
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .red-card { background: #fff0f0; border-left: 4px solid #e53e3e; }
    .yellow-card { background: #fffbeb; border-left: 4px solid #d69e2e; }
    .green-card { background: #f0fff4; border-left: 4px solid #38a169; }
    .clause-quote {
        font-size: 0.82rem;
        color: #666;
        font-style: italic;
        margin-top: 6px;
        padding: 6px 10px;
        background: rgba(0,0,0,0.04);
        border-radius: 6px;
    }
    h1 { font-size: 2.4rem !important; }
    .subtitle { color: #666; font-size: 1.05rem; margin-top: -12px; margin-bottom: 28px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_url_text(url: str) -> str:
    """Fetch and extract readable text from a URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:MAX_TEXT_CHARS]


def run_workflow(tc_text: str, source_url: str) -> dict:
    """Submit workflow via GraphN REST API (async mode) and poll for result."""
    endpoint = f"{GRAPHN_URL}/v1/{GRAPHN_WORKSPACE}/workflows/{WORKFLOW_ID}/run"
    payload = {
        "input": {"tc_text": tc_text, "source_url": source_url},
        "mode": "async",
    }
    resp = requests.post(endpoint, headers=HEADERS, json=payload, timeout=30)
    if resp.status_code == 405:
        # Fallback: try sync (may time out on long docs)
        payload["mode"] = "sync"
        resp = requests.post(endpoint, headers=HEADERS, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()

    resp.raise_for_status()
    data = resp.json()

    exec_id = data.get("execution_id") or data.get("id")
    if not exec_id:
        # Sync response returned directly
        return data

    # Poll for completion
    poll_url = f"{GRAPHN_URL}/v1/{GRAPHN_WORKSPACE}/executions/{exec_id}"
    for _ in range(120):
        time.sleep(3)
        poll = requests.get(poll_url, headers=HEADERS, timeout=15)
        poll.raise_for_status()
        result = poll.json()
        status = result.get("status", "")
        if status == "completed":
            return result
        if status in ("failed", "error"):
            raise RuntimeError(result.get("error") or "Workflow execution failed")

    raise TimeoutError("Analysis timed out after 6 minutes")


def extract_report(raw: dict) -> dict:
    """Pull the structured report out of the GraphN response."""
    output = raw.get("output", {})
    result = output.get("result", output)
    if isinstance(result, str):
        result = json.loads(result)
    return result


def risk_color(label: str) -> str:
    colors = {
        "Low Risk": "#38a169",
        "Medium Risk": "#d69e2e",
        "High Risk": "#e07b39",
        "Very High Risk": "#e53e3e",
    }
    return colors.get(label, "#888")


def risk_emoji(score: int) -> str:
    if score <= 3:
        return "🟢"
    if score <= 5:
        return "🟡"
    if score <= 7:
        return "🟠"
    return "🔴"


# ── UI ────────────────────────────────────────────────────────────────────────

st.markdown("# 🔍 Fine Print")
st.markdown('<p class="subtitle">Paste a Terms & Conditions URL or text — get the plain-English breakdown instantly.</p>', unsafe_allow_html=True)

tab_url, tab_text = st.tabs(["🔗 Paste a URL", "📄 Paste raw text"])

tc_text = ""
source_url = ""

with tab_url:
    url_input = st.text_input(
        "T&C URL",
        placeholder="https://www.instagram.com/legal/terms/",
        label_visibility="collapsed",
    )
    if url_input:
        source_url = url_input

with tab_text:
    raw_text_input = st.text_area(
        "Terms & Conditions text",
        height=220,
        placeholder="Paste the full Terms & Conditions text here…",
        label_visibility="collapsed",
    )

analyze_btn = st.button("Analyze →", type="primary", use_container_width=False)

if analyze_btn:
    if not GRAPHN_API_KEY or not GRAPHN_WORKSPACE:
        st.error("Missing GRAPHN_API_KEY or GRAPHN_WORKSPACE environment variables.")
        st.stop()

    active_url = url_input if tab_url else ""
    active_text = raw_text_input if tab_text else ""

    if active_url:
        with st.spinner("Fetching the T&C page…"):
            try:
                tc_text = fetch_url_text(active_url)
                source_url = active_url
            except Exception as e:
                st.error(f"Could not fetch the URL: {e}")
                st.stop()
    elif active_text.strip():
        tc_text = active_text.strip()
    else:
        st.warning("Paste a URL or some text first.")
        st.stop()

    if len(tc_text) < 100:
        st.warning("The text is too short to be a meaningful T&C document.")
        st.stop()

    with st.status("Analyzing the fine print…", expanded=True) as status:
        st.write("Sending to GraphN pipeline…")
        try:
            raw_result = run_workflow(tc_text, source_url)
            st.write("Parsing results…")
            report = extract_report(raw_result)
            status.update(label="Analysis complete", state="complete", expanded=False)
        except Exception as e:
            status.update(label="Analysis failed", state="error")
            st.error(f"Error: {e}")
            st.stop()

    # ── Results ───────────────────────────────────────────────────────────────
    score = report.get("risk_score", 0)
    label = report.get("risk_label", "Unknown")
    summary = report.get("executive_summary", "")
    red_flags = report.get("red_flags", [])
    yellow_flags = report.get("yellow_flags", [])
    green_items = report.get("green_items", [])
    categories = report.get("categories_affected", [])

    color = risk_color(label)

    st.divider()

    # Score header
    col_score, col_summary = st.columns([1, 3])
    with col_score:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div class="score-ring" style="color:{color};">{risk_emoji(score)} {score}/10</div>'
            f'<div class="risk-badge" style="background:{color}22; color:{color};">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if categories:
            st.markdown("**Areas affected:**")
            for cat in categories:
                st.markdown(f"- {cat.replace('_', ' ').title()}")

    with col_summary:
        st.markdown("### What you're actually agreeing to")
        st.markdown(f"> {summary}")
        if source_url:
            st.caption(f"Source: {source_url}")

    st.divider()

    # Flags
    col_left, col_right = st.columns(2)

    with col_left:
        if red_flags:
            st.markdown(f"### 🔴 Red Flags ({len(red_flags)})")
            for flag in red_flags:
                st.markdown(
                    f'<div class="flag-card red-card">'
                    f'<strong>{flag["title"]}</strong><br>'
                    f'{flag["plain_english"]}'
                    f'<div class="clause-quote">"{flag.get("clause_text", "")}"</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("### 🔴 Red Flags")
            st.success("No serious red flags found.")

        if green_items:
            st.markdown(f"### ✅ What's Fine ({len(green_items)})")
            for item in green_items:
                st.markdown(
                    f'<div class="flag-card green-card">'
                    f'<strong>{item["title"]}</strong><br>'
                    f'{item["plain_english"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    with col_right:
        if yellow_flags:
            st.markdown(f"### 🟡 Worth Knowing ({len(yellow_flags)})")
            for flag in yellow_flags:
                st.markdown(
                    f'<div class="flag-card yellow-card">'
                    f'<strong>{flag["title"]}</strong><br>'
                    f'{flag["plain_english"]}'
                    f'<div class="clause-quote">"{flag.get("clause_text", "")}"</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("### 🟡 Worth Knowing")
            st.info("No notable yellow flags.")

    st.divider()
    with st.expander("Raw JSON report"):
        st.json(report)

    with st.expander("T&C text sent to analysis"):
        st.text(tc_text[:3000] + ("…" if len(tc_text) > 3000 else ""))
