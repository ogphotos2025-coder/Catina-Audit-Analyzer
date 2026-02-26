"""
Cantina Audit Explainer
A Streamlit app that transforms smart contract audit PDFs into plain-English explanations
anyone can understand — no technical background required.
"""

import streamlit as st
import fitz  # PyMuPDF
import re
import json
import os
from anthropic import Anthropic

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Audit Explainer · Cantina",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=DM+Sans:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: #0a0a0f; color: #e8e8f0; }

    /* Hero */
    .hero {
        background: linear-gradient(135deg, #0d0d1a 0%, #12001f 50%, #000d1a 100%);
        border: 1px solid #2a1f4a;
        border-radius: 16px;
        padding: 2.5rem 3rem;
        margin-bottom: 2rem;
    }
    .hero h1 {
        font-size: 2.4rem; font-weight: 700;
        background: linear-gradient(90deg, #a855f7, #ec4899, #f97316);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 0 0 0.5rem 0;
    }
    .hero p { color: #9ca3af; font-size: 1.05rem; margin: 0; }

    /* Verdict banner */
    .verdict-red   { background:#1a0505; border:1px solid #7f1d1d; border-radius:12px; padding:1.25rem 1.5rem; }
    .verdict-orange{ background:#1a0a00; border:1px solid #7c2d12; border-radius:12px; padding:1.25rem 1.5rem; }
    .verdict-yellow{ background:#1a1800; border:1px solid #78350f; border-radius:12px; padding:1.25rem 1.5rem; }
    .verdict-green { background:#001a0a; border:1px solid #14532d; border-radius:12px; padding:1.25rem 1.5rem; }

    .verdict-icon { font-size:2.5rem; margin-bottom:0.5rem; }
    .verdict-text { font-size:1.25rem; font-weight:700; margin-bottom:0.4rem; color:#f0f0f8; }
    .verdict-detail { font-size:0.95rem; color:#c4c4d4; line-height:1.7; }

    /* Finding card */
    .finding-card {
        background: #111120; border: 1px solid #1e1e35; border-radius: 10px;
        padding: 1.25rem 1.5rem; margin: 0.8rem 0;
    }
    .finding-card-title { font-size:1.05rem; font-weight:600; color:#e8e8f0; margin-bottom:0.75rem; }

    .risk-severe { background:#3b0a0a; color:#f87171; border:1px solid #7f1d1d; border-radius:20px; padding:2px 12px; font-size:0.75rem; font-weight:700; letter-spacing:0.05em; }
    .risk-high   { background:#2d1a00; color:#fb923c; border:1px solid #7c2d12; border-radius:20px; padding:2px 12px; font-size:0.75rem; font-weight:700; letter-spacing:0.05em; }
    .risk-medium { background:#2d2a00; color:#fbbf24; border:1px solid #78350f; border-radius:20px; padding:2px 12px; font-size:0.75rem; font-weight:700; letter-spacing:0.05em; }

    .section-label {
        font-size:0.72rem; font-weight:700; letter-spacing:0.1em; text-transform:uppercase;
        color:#7c3aed; margin: 0.9rem 0 0.3rem 0;
    }
    .section-text { font-size:0.92rem; color:#c4c4d4; line-height:1.75; }

    /* Takeaway bullets */
    .takeaway-item {
        background:#111120; border-left:3px solid #a855f7;
        border-radius:0 8px 8px 0; padding:0.75rem 1rem;
        margin:0.5rem 0; font-size:0.95rem; color:#d4d4e8; line-height:1.6;
    }

    /* Scorecard table */
    .score-table { width:100%; border-collapse:collapse; }
    .score-table th {
        background:#0d0d1e; color:#7c3aed; font-size:0.75rem; font-weight:700;
        letter-spacing:0.08em; text-transform:uppercase; padding:0.6rem 1rem;
        border-bottom:1px solid #2a2a45; text-align:left;
    }
    .score-table td { padding:0.65rem 1rem; border-bottom:1px solid #1a1a30; font-size:0.9rem; color:#d4d4e8; }
    .score-table tr:hover td { background:#111124; }
    .status-fixed    { color:#34d399; font-weight:600; }
    .status-open     { color:#f87171; font-weight:600; }
    .status-partial  { color:#fbbf24; font-weight:600; }

    /* Metric box */
    .metric-box {
        background: #111120; border: 1px solid #1e1e35; border-radius: 8px;
        padding: 1rem; text-align: center;
    }
    .metric-num   { font-size: 2rem; font-weight: 700; color: #a855f7; }
    .metric-label { font-size: 0.8rem; color: #6b7280; margin-top: 0.25rem; }

    /* Button */
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #a855f7);
        color: white; border: none; border-radius: 8px;
        font-weight: 600; padding: 0.65rem 1.75rem;
        transition: opacity 0.2s; font-size: 1rem;
    }
    .stButton > button:hover { opacity: 0.85; }

    hr { border-color: #1e1e35; }
    .stSpinner > div { color: #a855f7 !important; }
    [data-testid="stSidebar"] { background: #0a0a14; border-right: 1px solid #1e1e35; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; background: transparent; }
    .stTabs [data-baseweb="tab"] {
        background: #111120; border: 1px solid #1e1e35; border-radius: 8px;
        color: #9ca3af; font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #4c1d95, #7c3aed) !important;
        border-color: #7c3aed !important; color: white !important;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PDF PARSING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

SEVERITY_PATTERN = re.compile(
    r'\b(Critical|High|Medium|Low|Informational|Info|Note)\b',
    re.IGNORECASE
)

DRAMA_KEYWORDS = [
    'drain', 'steal', 'theft', 'reentrancy', 're-entrancy', 'arbitrary',
    'bypass', 'overflow', 'underflow', 'manipulation', 'front-run', 'frontrun',
    'flash loan', 'unauthorized', 'exploit', 'attacker', 'malicious', 'loss of funds',
    'lock', 'freeze', 'bricked', 'infinite', 'privilege escalation', 'takeover',
]


def extract_text_from_pdf(pdf_bytes: bytes) -> list[dict]:
    pages = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text")
            pages.append({"page": i + 1, "text": text})
    return pages


def parse_findings(pages: list[dict]) -> list[dict]:
    full_text = "\n".join(p["text"] for p in pages)

    page_offsets = []
    offset = 0
    for p in pages:
        page_offsets.append((offset, offset + len(p["text"]), p["page"]))
        offset += len(p["text"]) + 1

    def offset_to_page(pos):
        for start, end, pg in page_offsets:
            if start <= pos < end:
                return pg
        return 1

    findings = []

    # Pass 1: Structured section parsing
    section_splits = re.split(
        r'\n(?=(?:[CHML]-\d+|C\d+|H\d+|M\d+)\s*[:\-–\s])',
        full_text
    )

    if len(section_splits) > 3:
        for chunk in section_splits:
            chunk = chunk.strip()
            if not chunk:
                continue

            sev_match = SEVERITY_PATTERN.search(chunk[:300])
            if not sev_match:
                continue
            severity = sev_match.group(1).capitalize()
            if severity.lower() in ('low', 'informational', 'info', 'note'):
                continue

            first_line = chunk.split('\n')[0].strip()
            title = re.sub(r'^[CHML]-?\d+\s*[:\-–\s]+', '', first_line).strip()
            if not title:
                title = chunk[:80].strip()

            desc_match = re.search(
                r'(?:Description|Impact|Detail)[s]?[:\s]*(.+?)(?=Recommendation|Mitigation|Fix|\Z)',
                chunk, re.DOTALL | re.IGNORECASE
            )
            description = desc_match.group(1).strip()[:1500] if desc_match else chunk[len(first_line):].strip()[:1500]

            rec_match = re.search(
                r'(?:Recommendation|Mitigation|Fix)[s]?[:\s]*(.+?)(?=\n[CHML]-|\Z)',
                chunk, re.DOTALL | re.IGNORECASE
            )
            recommendation = rec_match.group(1).strip()[:800] if rec_match else ""

            pos = full_text.find(first_line[:40])
            page = offset_to_page(max(0, pos)) if pos >= 0 else 1

            drama_score = sum(1 for kw in DRAMA_KEYWORDS if kw in chunk.lower())

            findings.append({
                "severity": severity,
                "title": title,
                "description": description,
                "recommendation": recommendation,
                "page": page,
                "drama_score": drama_score,
                "raw_chunk": chunk[:2000],
            })

    # Pass 2: Paragraph fallback
    if len(findings) < 2:
        paragraphs = re.split(r'\n{2,}', full_text)
        for para in paragraphs:
            sev_match = SEVERITY_PATTERN.search(para[:200])
            if not sev_match:
                continue
            severity = sev_match.group(1).capitalize()
            if severity.lower() in ('low', 'informational', 'info', 'note'):
                continue
            if len(para.strip()) < 80:
                continue

            lines = [l.strip() for l in para.strip().split('\n') if l.strip()]
            title = lines[0][:120] if lines else para[:80]
            description = '\n'.join(lines[1:])[:1500] if len(lines) > 1 else para[:1500]
            drama_score = sum(1 for kw in DRAMA_KEYWORDS if kw in para.lower())
            pos = full_text.find(para[:40])
            page = offset_to_page(max(0, pos)) if pos >= 0 else 1

            findings.append({
                "severity": severity,
                "title": title,
                "description": description,
                "recommendation": "",
                "page": page,
                "drama_score": drama_score,
                "raw_chunk": para[:2000],
            })

    # Deduplicate
    seen = set()
    unique = []
    for f in findings:
        key = f["title"][:40].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(f)

    return unique


def select_top_findings(findings: list[dict], n: int = 5) -> list[dict]:
    sev_rank = {"Critical": 3, "High": 2, "Medium": 1}

    def score(f):
        return (
            sev_rank.get(f["severity"], 0) * 10 +
            f["drama_score"] * 2 +
            min(len(f["description"]) // 100, 5)
        )

    return sorted(findings, key=score, reverse=True)[:n]


# ══════════════════════════════════════════════════════════════════════════════
#  AI — PLAIN-LANGUAGE SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a friendly security explainer. Your job is to read technical smart contract audit findings and translate them into plain English that anyone can understand — no coding or blockchain knowledge needed.

## YOUR VOICE
- Write as if you are explaining to a smart friend who has never written a line of code.
- Never use jargon without immediately explaining it in parentheses.
- Be honest and direct. If something is serious, say so clearly. If it was fixed, reassure the reader.
- Use short sentences. Avoid passive voice.
- Never use: "reentrancy", "smart contract" (use "the program" or "the app"), "on-chain", "Solidity", "EVM", "bytecode", "opcode", "calldata", technical function names.

## WHAT TO PRODUCE

### Overall Verdict
Give an overall safety verdict based on the findings. Use one of:
- 🔴 Serious Concerns — Critical or unresolved issues found
- 🟠 Needs Attention — High severity issues present
- 🟡 Minor Issues — Medium/low issues only
- 🟢 Looks Good — Issues found and all resolved

### Per-Finding Plain Explanation
For EACH finding, write:
- A short, plain-English title (rewrite the technical title so anyone gets it immediately)
- What happened: what was the flaw, in simple terms (2-3 sentences max)
- What an attacker could do: the real-world consequence if exploited — use dollar amounts or analogies if helpful
- What was done to fix it: explain the fix simply, or say "This has not been fixed yet" if unresolved

### Practical Takeaways
3-5 bullet points telling a non-technical reader what they should actually do or know based on this report. Examples: "Wait until the team fixes issue X before depositing money", "All critical issues have been resolved — the code is safer now", "Ask the team for a follow-up audit".

### Risk Scorecard
A simple list of all findings with: plain-English name | Risk level (Severe / High / Medium) | Status (Fixed / Not Fixed / Partially Fixed)

## OUTPUT FORMAT — return ONLY this JSON, no preamble, no markdown fences:
{
  "overall_verdict": "🔴 Serious Concerns",
  "verdict_detail": "Two clear sentences summarising the audit outcome for a non-technical reader.",
  "findings_plain": [
    {
      "plain_title": "Anyone could empty the wallet",
      "severity_label": "Severe Risk",
      "what_happened": "...",
      "what_attacker_could_do": "...",
      "what_was_fixed": "..."
    }
  ],
  "practical_takeaways": ["...", "..."],
  "risk_scorecard": [
    {"finding": "Anyone could empty the wallet", "risk": "Severe", "status": "Fixed"}
  ]
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  AI GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def build_user_prompt(findings: list[dict], project_name: str) -> str:
    findings_text = ""
    for i, f in enumerate(findings, 1):
        findings_text += f"""
--- ISSUE {i} ---
Severity: {f['severity']}
Title: {f['title']}
Description:
{f['description']}

Recommendation:
{f.get('recommendation', 'Not specified')}
"""

    return f"""Please explain the following security audit findings in plain English so anyone can understand them.

Project Name: {project_name if project_name else "Unknown Project"}

FINDINGS:
{findings_text}

Return ONLY the JSON object as specified. No preamble."""


def generate_content(findings: list[dict], project_name: str, api_key: str) -> dict:
    client = Anthropic(api_key=api_key)
    user_prompt = build_user_prompt(findings, project_name)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


# ══════════════════════════════════════════════════════════════════════════════
#  UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

SEVERITY_TO_RISK = {
    "Critical": ("Severe Risk", "risk-severe", "🔴"),
    "High":     ("High Risk",   "risk-high",   "🟠"),
    "Medium":   ("Medium Risk", "risk-medium",  "🟡"),
}

def render_finding_preview(f: dict):
    sev = f["severity"]
    label, css, icon = SEVERITY_TO_RISK.get(sev, ("Medium Risk", "risk-medium", "🟡"))
    st.markdown(f"""
    <div class="finding-card">
        <span class="{css}">{icon} {label}</span>
        <div class="finding-card-title" style="margin-top:0.6rem;">{f['title']}</div>
        <div style="font-size:0.85rem; color:#6b7280; margin-top:0.3rem;">Page {f['page']} of the report</div>
    </div>
    """, unsafe_allow_html=True)


def verdict_class(verdict: str) -> str:
    v = verdict.lower()
    if "serious" in v or "🔴" in verdict:
        return "verdict-red"
    if "attention" in v or "🟠" in verdict:
        return "verdict-orange"
    if "minor" in v or "🟡" in verdict:
        return "verdict-yellow"
    return "verdict-green"


def status_class(status: str) -> str:
    s = status.lower()
    if "not" in s or "unresolved" in s or "open" in s:
        return "status-open"
    if "partial" in s:
        return "status-partial"
    return "status-fixed"


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔍 Audit Explainer")
        st.markdown("<div style='color:#6b7280; font-size:0.85rem;'>Turn any audit PDF into plain English</div>", unsafe_allow_html=True)
        st.divider()

        # Pre-fill from Streamlit secrets or environment variable
        default_key = ""
        try:
            default_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass
        if not default_key:
            default_key = os.environ.get("ANTHROPIC_API_KEY", "")

        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=default_key,
            placeholder="sk-ant-...",
            help="Get your key at console.anthropic.com. Nothing is stored."
        )

        st.divider()
        project_name = st.text_input("Project Name (optional)", placeholder="e.g. VaultX Finance")
        max_findings = st.slider(
            "How many issues to analyse",
            2, 8, 4,
            help="More issues = more detail but takes slightly longer"
        )
        st.divider()
        st.markdown("<div style='color:#4b5563; font-size:0.75rem;'>Powered by Claude AI & PyMuPDF</div>", unsafe_allow_html=True)

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero">
        <h1>Audit Explainer</h1>
        <p>Upload a security audit PDF. Get a plain-English breakdown anyone can understand — no technical background needed.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Upload ────────────────────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Drop your audit PDF here",
        type=["pdf"],
        label_visibility="collapsed"
    )

    if not uploaded_file:
        st.markdown("""
        <div style="text-align:center; padding:3rem; border:1px dashed #2a2a45; border-radius:12px; color:#4b5563;">
            <div style="font-size:3rem; margin-bottom:1rem;">📄</div>
            <div style="font-size:1.1rem; color:#6b7280;">Upload a security audit PDF to get started</div>
            <div style="font-size:0.85rem; margin-top:0.5rem; color:#4b5563;">Supports Cantina, Code4rena, Sherlock and most audit formats</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Parse PDF ─────────────────────────────────────────────────────────────
    with st.spinner("Reading through the audit report…"):
        pdf_bytes = uploaded_file.read()
        pages = extract_text_from_pdf(pdf_bytes)
        all_findings = parse_findings(pages)
        top_findings = select_top_findings(all_findings, n=max_findings)

    # ── Summary metrics ───────────────────────────────────────────────────────
    total_pages = len(pages)
    n_critical = sum(1 for f in all_findings if f["severity"] == "Critical")
    n_high     = sum(1 for f in all_findings if f["severity"] == "High")
    n_medium   = sum(1 for f in all_findings if f["severity"] == "Medium")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-num">{total_pages}</div><div class="metric-label">Pages Scanned</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-num" style="color:#f87171">{n_critical}</div><div class="metric-label">🔴 Severe Issues</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><div class="metric-num" style="color:#fb923c">{n_high}</div><div class="metric-label">🟠 High Risk Issues</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-box"><div class="metric-num" style="color:#fbbf24">{n_medium}</div><div class="metric-label">🟡 Medium Issues</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Issues found preview ──────────────────────────────────────────────────
    with st.expander(f"📋 {len(top_findings)} issues selected for analysis", expanded=False):
        if top_findings:
            for f in top_findings:
                render_finding_preview(f)
        else:
            st.warning("No significant issues detected. The PDF may use non-standard formatting.")

    if not all_findings:
        st.error("Could not extract any issues from this PDF. The document may be a scanned image rather than a text-based PDF.")
        return

    # ── Generate button ───────────────────────────────────────────────────────
    st.divider()

    if not api_key:
        st.warning("⚠️ Add your Anthropic API key in the sidebar to generate the plain-English explanation.")
        return

    col_btn, col_hint = st.columns([1, 3])
    with col_btn:
        generate = st.button("🔍 Explain This Audit", use_container_width=True)
    with col_hint:
        st.markdown("<div style='color:#6b7280; font-size:0.9rem; padding-top:0.75rem;'>Generates a plain-English breakdown, risk verdict, and practical takeaways</div>", unsafe_allow_html=True)

    if not generate and "content" not in st.session_state:
        return

    # ── AI generation ─────────────────────────────────────────────────────────
    if generate:
        with st.spinner("🤖 Analysing the audit and writing plain-English explanations…"):
            try:
                content = generate_content(top_findings, project_name, api_key)
                st.session_state["content"] = content
            except json.JSONDecodeError as e:
                st.error(f"The AI returned an unexpected format. Please try again. (Detail: {e})")
                return
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                return

    content = st.session_state.get("content", {})
    if not content:
        return

    st.success("✅ Explanation ready!")
    st.divider()

    # ── Verdict banner ────────────────────────────────────────────────────────
    verdict = content.get("overall_verdict", "")
    detail  = content.get("verdict_detail", "")
    vclass  = verdict_class(verdict)

    st.markdown(f"""
    <div class="{vclass}">
        <div class="verdict-icon">{verdict.split()[0] if verdict else "🔍"}</div>
        <div class="verdict-text">{verdict}</div>
        <div class="verdict-detail">{detail}</div>
    </div>
    <br>
    """, unsafe_allow_html=True)

    # ── Three tabs ────────────────────────────────────────────────────────────
    tab_overview, tab_findings, tab_scorecard = st.tabs([
        "📋 Overview & Takeaways",
        "🔎 Issue Breakdowns",
        "📊 Risk Scorecard",
    ])

    # ── Tab 1: Overview ───────────────────────────────────────────────────────
    with tab_overview:
        takeaways = content.get("practical_takeaways", [])
        if takeaways:
            st.markdown("### What You Should Know")
            st.markdown("<div style='color:#9ca3af; font-size:0.9rem; margin-bottom:1rem;'>Key points from this audit, in plain English.</div>", unsafe_allow_html=True)
            for item in takeaways:
                st.markdown(f'<div class="takeaway-item">✔ {item}</div>', unsafe_allow_html=True)
        else:
            st.info("No takeaways generated.")

    # ── Tab 2: Finding breakdowns ─────────────────────────────────────────────
    with tab_findings:
        findings_plain = content.get("findings_plain", [])
        if findings_plain:
            st.markdown("<div style='color:#9ca3af; font-size:0.9rem; margin-bottom:1rem;'>Click on each issue to read the full plain-English explanation.</div>", unsafe_allow_html=True)
            for fp in findings_plain:
                sev_label = fp.get("severity_label", "Medium Risk")
                icon = "🔴" if "Severe" in sev_label else ("🟠" if "High" in sev_label else "🟡")
                css  = "risk-severe" if "Severe" in sev_label else ("risk-high" if "High" in sev_label else "risk-medium")

                with st.expander(f"{icon} {fp.get('plain_title', 'Issue')}"):
                    st.markdown(f'<span class="{css}">{icon} {sev_label}</span>', unsafe_allow_html=True)

                    st.markdown('<div class="section-label">What happened</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="section-text">{fp.get("what_happened", "—")}</div>', unsafe_allow_html=True)

                    st.markdown('<div class="section-label">What an attacker could have done</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="section-text">{fp.get("what_attacker_could_do", "—")}</div>', unsafe_allow_html=True)

                    st.markdown('<div class="section-label">What was done to fix it</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="section-text">{fp.get("what_was_fixed", "—")}</div>', unsafe_allow_html=True)
        else:
            st.info("No detailed finding breakdowns available.")

    # ── Tab 3: Risk scorecard ─────────────────────────────────────────────────
    with tab_scorecard:
        scorecard = content.get("risk_scorecard", [])
        if scorecard:
            st.markdown("<div style='color:#9ca3af; font-size:0.9rem; margin-bottom:1rem;'>A quick-reference table of all issues found in this audit.</div>", unsafe_allow_html=True)

            rows = ""
            for row in scorecard:
                risk   = row.get("risk", "")
                status = row.get("status", "")
                risk_icon = "🔴" if "Severe" in risk else ("🟠" if "High" in risk else "🟡")
                scls = status_class(status)
                rows += f"""<tr>
                    <td>{row.get('finding', '—')}</td>
                    <td>{risk_icon} {risk}</td>
                    <td class="{scls}">{status}</td>
                </tr>"""

            st.markdown(f"""
            <table class="score-table">
                <thead><tr><th>Issue</th><th>Risk Level</th><th>Status</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
            """, unsafe_allow_html=True)
        else:
            st.info("No scorecard available.")

    # ── Export ────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Export")

    # Build a readable plain-text report
    takeaway_lines = "\n".join(f"• {t}" for t in content.get("practical_takeaways", []))
    findings_md = ""
    for fp in content.get("findings_plain", []):
        findings_md += f"""
### {fp.get('plain_title', 'Issue')} — {fp.get('severity_label', '')}

**What happened:** {fp.get('what_happened', '')}

**What an attacker could have done:** {fp.get('what_attacker_could_do', '')}

**What was done to fix it:** {fp.get('what_was_fixed', '')}

---
"""

    scorecard_md = "| Issue | Risk | Status |\n|---|---|---|\n"
    for row in content.get("risk_scorecard", []):
        scorecard_md += f"| {row.get('finding','—')} | {row.get('risk','—')} | {row.get('status','—')} |\n"

    markdown_export = f"""# Security Audit Report — Plain English Summary
**Project:** {project_name or "Unknown"}

## Overall Verdict
{content.get('overall_verdict', '')}

{content.get('verdict_detail', '')}

---

## What You Should Know
{takeaway_lines}

---

## Issue Breakdowns
{findings_md}

## Risk Scorecard
{scorecard_md}
"""

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.download_button(
            "⬇️ Download Plain-English Report (Markdown)",
            data=markdown_export,
            file_name=f"audit_plain_english_{project_name or 'report'}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_e2:
        st.download_button(
            "⬇️ Download Raw Data (JSON)",
            data=json.dumps(content, indent=2),
            file_name=f"audit_data_{project_name or 'report'}.json",
            mime="application/json",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
