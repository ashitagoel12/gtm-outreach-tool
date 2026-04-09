# ─────────────────────────────────────────────────────────────────────────────
# GTM Outreach Intelligence Tool — V2
# Streamlit app: structured ICP dropdowns, LinkedIn enrichment, seniority
# advisor, personalised 4-email sequence, HubSpot CRM sync.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import anthropic
import requests
import json
import re
from datetime import datetime, timedelta


# ── Secrets ───────────────────────────────────────────────────────────────────
def _secret(key: str) -> str:
    """Return a named secret from st.secrets, or '' if absent."""
    try:
        return st.secrets.get(key, "")
    except Exception:
        return ""

anthropic_key = _secret("ANTHROPIC_API_KEY")


# ── ICP dropdown option lists ─────────────────────────────────────────────────
COMPANY_SIZES  = ["1–10", "11–50", "51–200", "201–500", "501–1,000", "1,000–5,000", "5,000+"]
INDUSTRIES     = ["SaaS", "E-commerce", "Fintech", "Healthcare", "EdTech",
                  "Enterprise Software", "MarTech", "HR Tech", "Other"]
LOCATIONS      = ["US", "Canada", "UK", "Europe", "APAC", "Global", "Other"]
FUNDING_STAGES = ["Bootstrapped", "Pre-seed", "Seed", "Series A",
                  "Series B", "Series C+", "Public"]
TECH_STACK     = ["Salesforce", "HubSpot", "Slack", "Zoom", "AWS",
                  "Google Workspace", "Microsoft 365", "Other"]
PAIN_POINTS    = ["Pipeline visibility", "Revenue ops", "Sales efficiency",
                  "Customer retention", "Data quality", "Lead generation", "Other"]

SENIORITY_COLOURS = {
    "IC":          "#6366f1",
    "Manager":     "#8b5cf6",
    "Director":    "#06b6d4",
    "VP":          "#f59e0b",
    "C-Level":     "#ef4444",
}


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GTM Outreach Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #f8f9fc; }
  [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e8ecf0; }

  .hero {
    background: linear-gradient(135deg, #1a1f36 0%, #2d3561 100%);
    border-radius: 14px; padding: 32px 36px; margin-bottom: 28px; color: #fff;
  }
  .hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 6px 0; letter-spacing: -0.5px; }
  .hero p  { font-size: 1rem; color: #b0bcd4; margin: 0; }

  .v2-badge {
    display: inline-block; background: linear-gradient(135deg,#6366f1,#8b5cf6);
    color: #fff; font-size: .65rem; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; padding: 3px 10px; border-radius: 20px;
    margin-left: 10px; vertical-align: middle;
  }

  .card {
    background: #fff; border: 1px solid #e8ecf0; border-radius: 12px;
    padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.04);
  }
  .card-title {
    font-size: .7rem; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #7c8db0; margin-bottom: 14px;
  }

  /* ICP section header */
  .icp-header {
    font-size: .7rem; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #4338ca;
    border-bottom: 2px solid #e0e7ff; padding-bottom: 8px; margin: 20px 0 14px 0;
  }

  /* Score badge */
  .score-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 70px; height: 70px; border-radius: 50%;
    font-size: 1.75rem; font-weight: 800; color: #fff; margin-bottom: 10px;
  }
  .score-high   { background: linear-gradient(135deg,#22c55e,#16a34a); }
  .score-medium { background: linear-gradient(135deg,#f59e0b,#d97706); }
  .score-low    { background: linear-gradient(135deg,#ef4444,#dc2626); }

  /* Seniority advisor card */
  .seniority-card {
    background: linear-gradient(135deg,#fdf4ff,#f0f4ff);
    border: 1px solid #ddd6fe; border-left: 4px solid #8b5cf6;
    border-radius: 12px; padding: 22px 26px; margin-bottom: 20px;
  }
  .seniority-level {
    display: inline-flex; align-items: center; gap: 8px;
    background: #fff; border: 2px solid currentColor;
    border-radius: 8px; padding: 6px 14px;
    font-size: 1rem; font-weight: 700; margin: 8px 6px 0 0;
  }

  /* Email card */
  .email-card {
    background: #fff; border: 1px solid #e8ecf0;
    border-left: 4px solid #6366f1; border-radius: 10px;
    padding: 20px 24px; margin-bottom: 16px;
  }
  .email-seq     { font-size:.65rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:#6366f1; margin-bottom:4px; }
  .email-timing  { font-size:.78rem; color:#6b7280; margin-bottom:10px; }
  .email-subject { font-size:1rem; font-weight:600; color:#1a1f36; margin-bottom:8px; }
  .email-body    { font-size:.875rem; color:#374151; white-space:pre-wrap; line-height:1.65; }

  /* HubSpot */
  .hs-banner {
    background: linear-gradient(135deg,#ff7a59,#ff5c35);
    border-radius: 12px; padding: 20px 24px; display: flex;
    align-items: center; gap: 16px; margin-bottom: 20px; color: #fff;
  }
  .hs-banner h3 { margin:0; font-size:1rem; font-weight:700; }
  .hs-banner p  { margin:0; font-size:.82rem; opacity:.9; }

  /* LinkedIn pull success */
  .linkedin-success {
    background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px;
    padding: 10px 14px; font-size: .82rem; color: #166534; margin-top: 6px;
  }

  /* Chips */
  .chip {
    display:inline-block; background:#eef2ff; color:#4338ca;
    border-radius:20px; padding:3px 10px; font-size:.72rem;
    font-weight:600; margin:3px;
  }

  .section-divider { border:none; border-top:1px solid #e8ecf0; margin: 28px 0; }
  label { font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)


# ── Utility helpers ───────────────────────────────────────────────────────────

def score_class(score: int) -> str:
    if score >= 7: return "score-high"
    if score >= 4: return "score-medium"
    return "score-low"


def extract_json_block(text: str) -> dict:
    """Extract first JSON object from Claude's response (fenced or bare)."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m: return json.loads(m.group(1))
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m: return json.loads(m.group(0))
    raise ValueError("No JSON object found in response")


def build_icp_string(
    company_size: str,
    industries: list,
    location: str,
    funding_stage: str,
    tech_stack: list,
    pain_points: list,
) -> str:
    """
    Assemble the structured ICP dropdown selections into a single human-readable
    string that can be passed directly into the Claude analysis prompt.
    """
    parts = []
    if company_size:                parts.append(f"Company size: {company_size} employees")
    if industries:                  parts.append(f"Industry: {', '.join(industries)}")
    if location:                    parts.append(f"Location: {location}")
    if funding_stage:               parts.append(f"Funding stage: {funding_stage}")
    if tech_stack:                  parts.append(f"Uses: {', '.join(tech_stack)}")
    if pain_points:                 parts.append(f"Key pain points: {', '.join(pain_points)}")
    return "; ".join(parts) if parts else "No specific ICP criteria defined"


# ── LinkedIn enrichment (placeholder — Apollo/Clay integration in V3) ─────────

def is_linkedin_url(text: str) -> bool:
    """Return True if the input looks like a LinkedIn profile URL."""
    return "linkedin.com/in/" in text.lower()


def extract_from_linkedin_url(url: str) -> dict:
    """
    Placeholder LinkedIn enrichment function.
    Parses the profile handle from the URL and converts it to a display name.
    In V3 this will call Apollo.io or Clay's enrichment API for full profile data.

    Returns a dict with: success, name, title, message.
    """
    try:
        # Pull the slug: linkedin.com/in/sarah-chen-ab1234 → "sarah-chen-ab1234"
        handle = url.rstrip("/").split("/in/")[-1].split("/")[0].split("?")[0]
        # Drop trailing numeric IDs (e.g. "sarah-chen-12345" → ["sarah", "chen"])
        name_parts = [p for p in handle.split("-") if not p.isdigit()]
        name = " ".join(p.capitalize() for p in name_parts if p) or "LinkedIn User"
        return {
            "success": True,
            "name":    name,
            "title":   "",      # can't reliably extract from URL alone
            "message": (
                f"✓ Name extracted from LinkedIn URL: <strong>{name}</strong>. "
                "Full enrichment (title, company, email) via Apollo/Clay coming in V3."
            ),
        }
    except Exception as exc:
        return {"success": False, "name": "", "title": "",
                "message": f"Could not parse LinkedIn URL: {exc}"}


# ── Claude API calls ──────────────────────────────────────────────────────────

def run_icp_analysis(client: anthropic.Anthropic, product: str, icp: str, company_url: str) -> dict:
    """
    Score how well the target company matches the ICP.
    Returns: score, verdict, summary, strengths, gaps, recommended_angle.
    """
    prompt = f"""You are a GTM analyst. Analyze how well a target company fits a vendor's ICP.

VENDOR PRODUCT:
{product}

ICP CRITERIA:
{icp}

TARGET COMPANY URL: {company_url}

Based on the company URL and what you can reasonably infer, score the ICP fit.

Return ONLY valid JSON (no markdown, no extra text):
{{
  "score": <integer 1-10>,
  "verdict": "<Strong Fit | Moderate Fit | Weak Fit>",
  "summary": "<2-sentence overall assessment>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "gaps": ["<gap 1>", "<gap 2>"],
  "recommended_angle": "<The single most compelling angle to lead with in outreach>"
}}"""

    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        text = next((b.text for b in stream.get_final_message().content if b.type == "text"), "")
    return extract_json_block(text)


def run_seniority_advisor(
    client: anthropic.Anthropic,
    analysis: dict,
    product: str,
) -> dict:
    """
    Recommend the optimal contact seniority level to target based on the
    ICP fit result and product description.

    Returns: primary_level, secondary_level, reasoning.
    """
    prompt = f"""You are a B2B sales strategist. Recommend the ideal contact seniority
level to target for outreach based on this ICP analysis and product.

PRODUCT: {product}

ICP FIT:
Score: {analysis.get('score')}/10 — {analysis.get('verdict')}
Summary: {analysis.get('summary')}
Recommended angle: {analysis.get('recommended_angle')}

Seniority options: IC (Individual Contributor), Manager, Director, VP, C-Level

Return ONLY valid JSON (no markdown):
{{
  "primary_level": "<IC | Manager | Director | VP | C-Level>",
  "secondary_level": "<IC | Manager | Director | VP | C-Level | null>",
  "reasoning": "<2-sentence explanation of why this level is optimal>"
}}"""

    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        text = next((b.text for b in stream.get_final_message().content if b.type == "text"), "")
    return extract_json_block(text)


def run_sequence_generation(
    client: anthropic.Anthropic,
    product: str,
    icp: str,
    company_url: str,
    contact_name: str,
    contact_role: str,
    angle: str,
) -> list:
    """
    Generate a 4-email cold outreach sequence.
    Returns list of dicts: sequence, send_day, send_label, subject, body.
    """
    first_name = contact_name.strip().split()[0] if contact_name.strip() else "there"

    prompt = f"""You are an elite B2B sales copywriter. Write a 4-email cold outreach sequence.

VENDOR PRODUCT: {product}
ICP CRITERIA: {icp}
TARGET COMPANY: {company_url}
CONTACT: {contact_name}, {contact_role}
LEADING ANGLE: {angle}

Guidelines:
- Email 1 (Day 1): Hyper-personalised opener, reference their company, one clear value prop, soft CTA
- Email 2 (Day 4): Concrete data point or insight relevant to their role, reply-to-thread CTA
- Email 3 (Day 9): Brief social proof / mini case study, direct ask for a call
- Email 4 (Day 17): Polite breakup email, leave door open, very short

Each email: under 150 words, human tone, NO "I hope this finds you well".
Use first name: {first_name}

Return ONLY valid JSON (no markdown):
[
  {{"sequence":1,"send_day":1,"send_label":"Day 1 — Initial Outreach","subject":"<subject>","body":"<body with \\n line breaks>"}},
  {{"sequence":2,"send_day":4,"send_label":"Day 4 — Value Add Follow-up","subject":"<subject>","body":"<body>"}},
  {{"sequence":3,"send_day":9,"send_label":"Day 9 — Social Proof","subject":"<subject>","body":"<body>"}},
  {{"sequence":4,"send_day":17,"send_label":"Day 17 — Graceful Breakup","subject":"<subject>","body":"<body>"}}
]"""

    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        text = next((b.text for b in stream.get_final_message().content if b.type == "text"), "")

    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if m: return json.loads(m.group(1))
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m: return json.loads(m.group(0))
    raise ValueError("No JSON array found in sequence response")


# ── HubSpot CRM integration ───────────────────────────────────────────────────

def hubspot_create_contact(
    api_key: str, contact_name: str, contact_role: str, company_url: str
) -> tuple:
    """
    Create a contact in HubSpot CRM v3.
    Returns (success: bool, contact_id: str, message: str).
    409 = already exists — treated as success, returns existing ID.
    """
    parts     = contact_name.strip().split(None, 1)
    firstname = parts[0] if parts else contact_name
    lastname  = parts[1] if len(parts) > 1 else ""
    company   = company_url.replace("https://", "").replace("http://", "").split("/")[0]

    payload = {"properties": {
        "firstname": firstname, "lastname": lastname,
        "jobtitle": contact_role, "company": company,
        "website": company_url, "hs_lead_status": "NEW",
    }}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = requests.post("https://api.hubapi.com/crm/v3/objects/contacts",
                          headers=headers, json=payload, timeout=15)
        if r.status_code in (200, 201):
            cid = r.json().get("id", "")
            return True, cid, f"Contact created (ID: {cid})"
        if r.status_code == 409:
            existing = r.json().get("message", "").split(":")[-1].strip()
            return True, existing, "Contact already exists — using existing record"
        return False, "", f"HubSpot error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, "", f"Request failed: {e}"


def hubspot_log_email_note(
    api_key: str, contact_id: str, seq: dict, contact_name: str
) -> tuple:
    """Log one email as a Note on a HubSpot contact. Returns (success, message)."""
    body_text = (
        f"[Outreach Sequence — {seq['send_label']}]\n"
        f"Subject: {seq['subject']}\n\n{seq['body']}"
    )
    payload = {
        "properties": {
            "hs_note_body":  body_text,
            "hs_timestamp":  datetime.utcnow().isoformat() + "Z",
        },
        "associations": [{
            "to":    {"id": contact_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}],
        }],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = requests.post("https://api.hubapi.com/crm/v3/objects/notes",
                          headers=headers, json=payload, timeout=15)
        if r.status_code in (200, 201):
            return True, f"Email {seq['sequence']} logged (Note ID: {r.json().get('id','')})"
        return False, f"Note error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"Request failed: {e}"


def push_to_hubspot(
    api_key: str, contact_name: str, contact_role: str,
    company_url: str, emails: list
) -> list:
    """Create contact + log all emails as Notes. Returns [(icon, message), ...]."""
    log = []
    ok, contact_id, msg = hubspot_create_contact(api_key, contact_name, contact_role, company_url)
    log.append(("✅" if ok else "❌", msg))
    if not ok:
        return log
    for email in emails:
        e_ok, e_msg = hubspot_log_email_note(api_key, contact_id, email, contact_name)
        log.append(("✅" if e_ok else "❌", e_msg))
    return log


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### How it works")
    st.markdown("""
1. **Define ICP** — use dropdowns to describe your ideal customer
2. **Set target** — paste company URL and contact details
3. **Analyze** — Claude scores fit and recommends contact seniority
4. **Generate** — 4 personalised emails with send timing
5. **Sync** *(optional)* — push to HubSpot with your token
""")
    st.divider()
    st.caption("GTM Outreach Intelligence · V2")


# ── Hero ──────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <h1>🎯 GTM Outreach Intelligence <span class="v2-badge">V2</span></h1>
  <p>AI-powered ICP analysis, seniority advisor &amp; personalised email sequence generator</p>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# INPUT FORM
# Left column: product description + structured ICP dropdowns
# Right column: company URL + LinkedIn / contact enrichment
# ═════════════════════════════════════════════════════════════════════════════

col_a, col_b = st.columns([1, 1], gap="large")

# ── Left column: product + ICP ────────────────────────────────────────────────
with col_a:
    st.markdown('<div class="card-title">Your Product</div>', unsafe_allow_html=True)
    product_desc = st.text_area(
        "Product Description",
        height=110,
        placeholder="E.g. Acme is a revenue intelligence platform that helps B2B sales teams identify buying signals, prioritise outreach, and increase win rates by 30%.",
        help="Describe your product's core value proposition.",
    )

    # ICP section — structured dropdowns replace the old free-text field
    st.markdown('<div class="icp-header">🎯 ICP Criteria</div>', unsafe_allow_html=True)

    icp_size    = st.selectbox("Company Size", [""] + COMPANY_SIZES,
                               format_func=lambda x: "Any size" if x == "" else x,
                               help="Number of employees at the target company.")

    icp_industries = st.multiselect("Industry", INDUSTRIES,
                                    help="Select one or more industries that match your ICP.")

    icp_location   = st.selectbox("Location", [""] + LOCATIONS,
                                   format_func=lambda x: "Any location" if x == "" else x)

    icp_funding    = st.selectbox("Funding Stage", [""] + FUNDING_STAGES,
                                   format_func=lambda x: "Any stage" if x == "" else x)

    icp_tech       = st.multiselect("Tech Stack", TECH_STACK,
                                    help="Tools the ideal customer already uses.")

    icp_pain       = st.multiselect("Pain Points", PAIN_POINTS,
                                    help="Challenges your ICP is actively facing.")


# ── Right column: target company + contact ────────────────────────────────────
with col_b:
    st.markdown('<div class="card-title">Target</div>', unsafe_allow_html=True)

    company_url = st.text_input(
        "Target Company URL",
        placeholder="https://www.acme.com",
        help="Claude infers company context from the domain.",
    )

    st.markdown("")

    # ── LinkedIn enrichment input ─────────────────────────────────────────────
    # Accepts either a plain name OR a LinkedIn profile URL.
    # When a URL is entered, "Pull from LinkedIn" parses the handle into a name
    # (full enrichment via Apollo/Clay arrives in V3).

    li_input = st.text_input(
        "Contact Name or LinkedIn URL",
        placeholder="Sarah Chen  or  https://linkedin.com/in/sarahchen",
        help="Enter a name for manual input, or a LinkedIn URL to auto-extract details.",
        key="li_input_field",
    )

    # Show the Pull button only when the input looks like a LinkedIn URL
    if li_input and is_linkedin_url(li_input):
        pull_col, _ = st.columns([1, 2])
        with pull_col:
            pull_btn = st.button("🔗 Pull from LinkedIn", use_container_width=True,
                                  key="linkedin_pull_btn")
        if pull_btn:
            result = extract_from_linkedin_url(li_input)
            st.session_state["linkedin_data"] = result

        # Show enrichment status if data has been pulled
        if st.session_state.get("linkedin_data"):
            ld = st.session_state["linkedin_data"]
            icon = "✓" if ld["success"] else "✗"
            colour = "#166534" if ld["success"] else "#991b1b"
            bg     = "#f0fdf4"  if ld["success"] else "#fff1f2"
            border = "#bbf7d0"  if ld["success"] else "#fecaca"
            st.markdown(
                f'<div class="linkedin-success" style="background:{bg};border-color:{border};color:{colour};">'
                f'{ld["message"]}</div>',
                unsafe_allow_html=True,
            )
    else:
        # Clear stale LinkedIn data if the user switched back to a plain name
        if st.session_state.get("linkedin_data") and not is_linkedin_url(li_input):
            st.session_state.pop("linkedin_data", None)

    # Resolve final contact name:
    # - LinkedIn pull succeeded → use extracted name
    # - Otherwise → use whatever the user typed directly
    ld             = st.session_state.get("linkedin_data", {})
    contact_name   = ld.get("name", "") if (ld.get("success") and is_linkedin_url(li_input)) else li_input

    # Contact role is always shown — LinkedIn URL alone can't reliably provide it
    contact_role = st.text_input(
        "Contact Role / Title",
        placeholder="VP of Revenue Operations",
        help="Enter manually. Auto-fill coming in V3 with Apollo/Clay enrichment.",
    )


# ── Assemble ICP string from dropdowns ───────────────────────────────────────
# Done here (before can_run) so validation can check whether any ICP was set.
icp_string = build_icp_string(
    icp_size, icp_industries, icp_location,
    icp_funding, icp_tech, icp_pain,
)

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)


# ── Analyse button ────────────────────────────────────────────────────────────
# Requires: product description, company URL, and a contact name.
# ICP dropdowns are optional (default = "Any"); role is optional too.

can_run = all([product_desc.strip(), company_url.strip(), contact_name.strip()])

run_col, _ = st.columns([1, 3])
with run_col:
    run_btn = st.button(
        "⚡ Analyze & Generate",
        type="primary",
        disabled=not can_run,
        use_container_width=True,
    )

if not can_run and not run_btn:
    missing = []
    if not product_desc.strip(): missing.append("Product Description")
    if not company_url.strip():  missing.append("Company URL")
    if not contact_name.strip(): missing.append("Contact Name (or LinkedIn URL)")
    if missing:
        st.info(f"Complete to enable analysis: {' · '.join(missing)}", icon="ℹ️")


# ═════════════════════════════════════════════════════════════════════════════
# BLOCK 1 — Run Claude calls when button is clicked
# Stores all results in session_state; renders nothing itself.
# The display block (Block 2) handles all rendering on every re-run.
# ═════════════════════════════════════════════════════════════════════════════

if run_btn and can_run:
    client = anthropic.Anthropic(api_key=anthropic_key)

    # Clear stale results from any previous run
    for k in ("analysis", "seniority", "emails", "hs_sync_log"):
        st.session_state.pop(k, None)

    # Snapshot the inputs so the display block uses consistent values
    # even if the user edits the form fields after analysis completes.
    st.session_state["_product"]      = product_desc
    st.session_state["_icp_string"]   = icp_string
    st.session_state["_company_url"]  = company_url
    st.session_state["_contact_name"] = contact_name
    st.session_state["_contact_role"] = contact_role

    # ── Step 1: ICP analysis ──────────────────────────────────────────────────
    with st.spinner("Analyzing company-ICP fit…"):
        try:
            analysis = run_icp_analysis(client, product_desc, icp_string, company_url)
            st.session_state["analysis"] = analysis
        except Exception as e:
            st.error(f"ICP analysis failed: {e}")
            st.stop()

    # ── Step 2: Seniority advisor ─────────────────────────────────────────────
    with st.spinner("Identifying optimal contact seniority…"):
        try:
            seniority = run_seniority_advisor(client, st.session_state["analysis"], product_desc)
            st.session_state["seniority"] = seniority
        except Exception as e:
            # Non-fatal — show a warning but continue to email generation
            st.warning(f"Seniority advisor skipped: {e}")
            st.session_state["seniority"] = {}

    # ── Step 3: Email sequence ────────────────────────────────────────────────
    angle = st.session_state["analysis"].get("recommended_angle", "")
    with st.spinner("Generating personalised 4-email sequence…"):
        try:
            emails = run_sequence_generation(
                client, product_desc, icp_string, company_url,
                contact_name, contact_role, angle,
            )
            st.session_state["emails"] = emails
        except Exception as e:
            st.error(f"Email generation failed: {e}")
            st.stop()

elif run_btn and not can_run:
    st.error("Please complete the required fields before running the analysis.")


# ═════════════════════════════════════════════════════════════════════════════
# BLOCK 2 — Render results on every re-run whenever session_state has data
# This block is independent of run_btn, so it persists across widget interactions
# (typing the HubSpot token, clicking Push, etc.).
# ═════════════════════════════════════════════════════════════════════════════

if st.session_state.get("analysis") and st.session_state.get("emails"):

    analysis  = st.session_state["analysis"]
    seniority = st.session_state.get("seniority", {})
    emails    = st.session_state["emails"]

    # Use snapshotted values from analysis time
    _product      = st.session_state.get("_product",      product_desc)
    _icp_string   = st.session_state.get("_icp_string",   icp_string)
    _company_url  = st.session_state.get("_company_url",  company_url)
    _contact_name = st.session_state.get("_contact_name", contact_name)
    _contact_role = st.session_state.get("_contact_role", contact_role)

    score     = analysis.get("score", 0)
    css_class = score_class(score)
    angle     = analysis.get("recommended_angle", "")

    # ── ICP Fit Analysis ──────────────────────────────────────────────────────
    st.markdown("## ICP Fit Analysis")

    c1, c2 = st.columns([1, 2], gap="large")

    with c1:
        st.markdown(f"""
<div class="card" style="text-align:center;">
  <div class="card-title">ICP Fit Score</div>
  <div class="score-badge {css_class}">{score}</div>
  <div style="font-size:.75rem;color:#6b7280;margin-bottom:6px;">out of 10</div>
  <div style="font-size:1rem;font-weight:700;color:#1a1f36;">{analysis.get('verdict','—')}</div>
</div>
""", unsafe_allow_html=True)

    with c2:
        strengths_html = "".join(
            f'<span class="chip">✓ {s}</span>' for s in analysis.get("strengths", [])
        )
        gaps_html = "".join(
            f'<span class="chip" style="background:#fff1f2;color:#be123c;">✗ {g}</span>'
            for g in analysis.get("gaps", [])
        )
        st.markdown(f"""
<div class="card">
  <div class="card-title">Assessment</div>
  <p style="color:#374151;margin-bottom:14px;">{analysis.get('summary','')}</p>
  <div class="card-title">Strengths</div>
  <div style="margin-bottom:12px;">{strengths_html}</div>
  <div class="card-title">Gaps</div>
  <div>{gaps_html}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div class="card" style="background:#f0f4ff;border-color:#c7d2fe;">
  <div class="card-title" style="color:#4338ca;">🎯 Recommended Outreach Angle</div>
  <p style="color:#1e1b4b;font-size:.95rem;margin:0;">{angle}</p>
</div>
""", unsafe_allow_html=True)

    # ── Contact Seniority Advisor ─────────────────────────────────────────────
    if seniority:
        primary   = seniority.get("primary_level", "")
        secondary = seniority.get("secondary_level") or ""
        reasoning = seniority.get("reasoning", "")

        primary_colour   = SENIORITY_COLOURS.get(primary,   "#6366f1")
        secondary_colour = SENIORITY_COLOURS.get(secondary, "#8b5cf6")

        primary_badge = (
            f'<span class="seniority-level" style="color:{primary_colour};border-color:{primary_colour};">'
            f'⭐ {primary}</span>'
        ) if primary else ""

        secondary_badge = (
            f'<span class="seniority-level" style="color:{secondary_colour};border-color:{secondary_colour};">'
            f'{secondary}</span>'
        ) if secondary and secondary != "null" else ""

        st.markdown(f"""
<div class="seniority-card">
  <div class="card-title" style="color:#7c3aed;">💼 Recommended Contact Seniority</div>
  <div style="margin-bottom:12px;">{primary_badge}{secondary_badge}</div>
  <p style="color:#374151;font-size:.875rem;margin:0;">{reasoning}</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ── Email Sequence ────────────────────────────────────────────────────────
    st.markdown("## 📧 Personalised 4-Email Sequence")

    border_colors = ["#6366f1", "#8b5cf6", "#06b6d4", "#10b981"]

    for i, email in enumerate(emails):
        color     = border_colors[i % len(border_colors)]
        send_date = (datetime.today() + timedelta(days=email.get("send_day", 1) - 1)).strftime("%b %d, %Y")
        safe_body = email.get("body", "").replace("<", "&lt;").replace(">", "&gt;")

        st.markdown(f"""
<div class="email-card" style="border-left-color:{color};">
  <div class="email-seq">Email {email.get('sequence','')}</div>
  <div class="email-timing">⏱ {email.get('send_label','')} &nbsp;·&nbsp; Suggested send: {send_date}</div>
  <div class="email-subject">Subject: {email.get('subject','')}</div>
  <div class="email-body">{safe_body}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ── HubSpot Sync ──────────────────────────────────────────────────────────
    # Rendered here (outside run_btn block) so it persists across re-runs.
    # key="hs_token" preserves the typed token value in Streamlit widget state.
    st.markdown("## 🔶 HubSpot Integration *(optional)*")

    st.markdown(f"""
<div class="hs-banner">
  <div style="font-size:2rem;">🔶</div>
  <div>
    <h3>Sync to HubSpot</h3>
    <p>Creates a contact for <strong>{_contact_name}</strong> at <strong>{_company_url}</strong>
       and logs all 4 emails as Notes.</p>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="card" style="background:#fff7f0;border-color:#fde8d8;margin-bottom:16px;">
  <div class="card-title" style="color:#c2500a;">🔑 Where to find your token</div>
  <p style="color:#374151;font-size:.875rem;margin:0;">
    <strong>Settings → Integrations → Private Apps</strong>.
    Needs <code>crm.objects.contacts.write</code> and <code>crm.objects.notes.write</code> scopes.<br><br>
    <a href="https://knowledge.hubspot.com/integrations/how-do-i-get-my-hubspot-api-key"
       target="_blank" style="color:#c2500a;">📖 HubSpot API key documentation →</a>
  </p>
</div>
""", unsafe_allow_html=True)

    hs_token = st.text_input(
        "HubSpot Personal Access Token",
        type="password",
        placeholder="pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        help="Never stored server-side.",
        key="hs_token",
    )

    if hs_token:
        hs_col, _ = st.columns([1, 3])
        with hs_col:
            hs_btn = st.button("🔶 Push to HubSpot", type="secondary",
                               use_container_width=True, key="hs_push_btn")
        if hs_btn:
            st.session_state.pop("hs_sync_log", None)
            with st.spinner("Syncing with HubSpot…"):
                sync_log = push_to_hubspot(hs_token, _contact_name, _contact_role,
                                           _company_url, emails)
            st.session_state["hs_sync_log"] = sync_log
    else:
        st.info("Enter your HubSpot API key above to enable CRM sync.", icon="ℹ️")

    # Render sync log — persisted in session_state so it survives re-renders
    if st.session_state.get("hs_sync_log"):
        st.markdown("**Sync results:**")
        for icon, msg in st.session_state["hs_sync_log"]:
            (st.success if icon == "✅" else st.error)(f"{icon} {msg}")
