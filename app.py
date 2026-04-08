import streamlit as st
import anthropic
import requests
import json
import re
from datetime import datetime, timedelta

# ── Secrets: loaded silently from Streamlit Cloud secrets ────────────────────
def _secret(key: str) -> str:
    try:
        return st.secrets.get(key, "")
    except Exception:
        return ""

anthropic_key = _secret("ANTHROPIC_API_KEY")
hubspot_key   = _secret("HUBSPOT_API_KEY")

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
  /* Base */
  [data-testid="stAppViewContainer"] { background: #f8f9fc; }
  [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e8ecf0; }

  /* Header band */
  .hero {
    background: linear-gradient(135deg, #1a1f36 0%, #2d3561 100%);
    border-radius: 14px;
    padding: 32px 36px;
    margin-bottom: 28px;
    color: #ffffff;
  }
  .hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 6px 0; letter-spacing: -0.5px; }
  .hero p  { font-size: 1rem; color: #b0bcd4; margin: 0; }

  /* Cards */
  .card {
    background: #ffffff;
    border: 1px solid #e8ecf0;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,.04);
  }
  .card-title {
    font-size: .7rem;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #7c8db0;
    margin-bottom: 14px;
  }

  /* Score badge */
  .score-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 70px; height: 70px;
    border-radius: 50%;
    font-size: 1.75rem;
    font-weight: 800;
    color: #fff;
    margin-bottom: 10px;
  }
  .score-high   { background: linear-gradient(135deg,#22c55e,#16a34a); }
  .score-medium { background: linear-gradient(135deg,#f59e0b,#d97706); }
  .score-low    { background: linear-gradient(135deg,#ef4444,#dc2626); }

  /* Email card */
  .email-card {
    background: #ffffff;
    border: 1px solid #e8ecf0;
    border-left: 4px solid #6366f1;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
  }
  .email-card:nth-child(2) { border-left-color: #8b5cf6; }
  .email-card:nth-child(3) { border-left-color: #06b6d4; }
  .email-card:nth-child(4) { border-left-color: #10b981; }

  .email-seq    { font-size: .65rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:#6366f1; margin-bottom:4px; }
  .email-timing { font-size:.78rem; color:#6b7280; margin-bottom:10px; }
  .email-subject { font-size:1rem; font-weight:600; color:#1a1f36; margin-bottom:8px; }
  .email-body   { font-size:.875rem; color:#374151; white-space:pre-wrap; line-height:1.65; }

  /* HubSpot button area */
  .hs-banner {
    background: linear-gradient(135deg,#ff7a59,#ff5c35);
    border-radius: 12px;
    padding: 20px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
    color: #fff;
  }
  .hs-banner h3 { margin:0; font-size:1rem; font-weight:700; }
  .hs-banner p  { margin:0; font-size:.82rem; opacity:.9; }

  /* Sidebar inputs */
  .sidebar-section { font-size:.7rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:#7c8db0; margin: 18px 0 8px 0; }

  /* Tag chips */
  .chip {
    display:inline-block; background:#eef2ff; color:#4338ca;
    border-radius:20px; padding:3px 10px; font-size:.72rem;
    font-weight:600; margin:3px;
  }

  /* Divider */
  .section-divider { border:none; border-top:1px solid #e8ecf0; margin: 28px 0; }

  /* Subtle label */
  label { font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def score_class(score: int) -> str:
    if score >= 7:
        return "score-high"
    if score >= 4:
        return "score-medium"
    return "score-low"


def extract_json_block(text: str) -> dict:
    """Pull the first JSON object out of a markdown/text response."""
    # Try fenced code block first
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # Bare JSON object
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError("No JSON found in response")


def run_icp_analysis(client: anthropic.Anthropic, product: str, icp: str, company_url: str) -> dict:
    """Call Claude to score ICP fit and return structured analysis."""
    prompt = f"""You are a GTM analyst. Analyze how well a target company fits a vendor's ICP.

VENDOR PRODUCT:
{product}

ICP CRITERIA:
{icp}

TARGET COMPANY URL: {company_url}

Based on the company URL domain and what you can reasonably infer about the company, score the ICP fit.

Return ONLY valid JSON (no markdown, no extra text) with this exact schema:
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
        full_text = stream.get_final_message().content
        # get text block
        text = next((b.text for b in full_text if b.type == "text"), "")

    return extract_json_block(text)


def run_sequence_generation(
    client: anthropic.Anthropic,
    product: str,
    icp: str,
    company_url: str,
    contact_name: str,
    contact_role: str,
    angle: str,
) -> list[dict]:
    """Generate a 4-email outreach sequence."""
    first_name = contact_name.strip().split()[0] if contact_name.strip() else "there"

    prompt = f"""You are an elite B2B sales copywriter. Write a 4-email cold outreach sequence.

VENDOR PRODUCT: {product}
ICP CRITERIA: {icp}
TARGET COMPANY: {company_url}
CONTACT: {contact_name}, {contact_role}
LEADING ANGLE: {angle}

Guidelines:
- Email 1 (Day 1): Hyper-personalised opener, reference their company, one clear value prop, soft CTA
- Email 2 (Day 4): Add a concrete data point or insight relevant to their role, reply-to-thread CTA
- Email 3 (Day 9): Brief social proof / mini case study, direct ask for a call
- Email 4 (Day 17): Polite breakup email, leave door open, very short

Each email must be concise (under 150 words), human, and NOT use generic phrases like "I hope this finds you well".
Use first name: {first_name}

Return ONLY valid JSON (no markdown) with this exact schema:
[
  {{
    "sequence": 1,
    "send_day": 1,
    "send_label": "Day 1 — Initial Outreach",
    "subject": "<subject line>",
    "body": "<email body with \\n for line breaks>"
  }},
  {{
    "sequence": 2,
    "send_day": 4,
    "send_label": "Day 4 — Value Add Follow-up",
    "subject": "<subject line>",
    "body": "<email body>"
  }},
  {{
    "sequence": 3,
    "send_day": 9,
    "send_label": "Day 9 — Social Proof",
    "subject": "<subject line>",
    "body": "<email body>"
  }},
  {{
    "sequence": 4,
    "send_day": 17,
    "send_label": "Day 17 — Graceful Breakup",
    "subject": "<subject line>",
    "body": "<email body>"
  }}
]"""

    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        full_text = stream.get_final_message().content
        text = next((b.text for b in full_text if b.type == "text"), "")

    # Parse JSON array
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError("No JSON array found in sequence response")


# ── HubSpot ───────────────────────────────────────────────────────────────────

def hubspot_create_contact(api_key: str, contact_name: str, contact_role: str, company_url: str) -> tuple[bool, str, str]:
    """Create a HubSpot contact. Returns (success, contact_id, message)."""
    parts = contact_name.strip().split(None, 1)
    firstname = parts[0] if parts else contact_name
    lastname = parts[1] if len(parts) > 1 else ""
    company = company_url.replace("https://", "").replace("http://", "").split("/")[0]

    payload = {
        "properties": {
            "firstname": firstname,
            "lastname": lastname,
            "jobtitle": contact_role,
            "company": company,
            "website": company_url,
            "hs_lead_status": "NEW",
        }
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(
            "https://api.hubapi.com/crm/v3/objects/contacts",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if r.status_code in (200, 201):
            contact_id = r.json().get("id", "")
            return True, contact_id, f"Contact created (ID: {contact_id})"
        # 409 = already exists
        if r.status_code == 409:
            existing_id = r.json().get("message", "").split(":")[-1].strip()
            return True, existing_id, "Contact already exists — using existing record"
        return False, "", f"HubSpot error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, "", f"Request failed: {e}"


def hubspot_log_email_note(api_key: str, contact_id: str, seq: dict, contact_name: str) -> tuple[bool, str]:
    """Log an email as a Note engagement on a HubSpot contact."""
    body_text = (
        f"[Outreach Sequence — {seq['send_label']}]\n"
        f"Subject: {seq['subject']}\n\n"
        f"{seq['body']}"
    )
    payload = {
        "properties": {
            "hs_note_body": body_text,
            "hs_timestamp": datetime.utcnow().isoformat() + "Z",
        },
        "associations": [
            {
                "to": {"id": contact_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}],
            }
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(
            "https://api.hubapi.com/crm/v3/objects/notes",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if r.status_code in (200, 201):
            return True, f"Email {seq['sequence']} logged (Note ID: {r.json().get('id','')})"
        return False, f"Note error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"Request failed: {e}"


def push_to_hubspot(api_key: str, contact_name: str, contact_role: str, company_url: str, emails: list[dict]):
    """Create contact + log all 4 emails as notes. Returns log lines."""
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
1. **Fill in** your product, ICP, target company, and contact
2. **Analyze** — Claude scores ICP fit with reasoning
3. **Generate** — 4 personalised emails with send timing
4. **Sync** — Push contact + emails to HubSpot with one click
""")
    st.divider()
    st.caption("Powered by Claude Sonnet 4.5")


# ── Main layout ───────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <h1>🎯 GTM Outreach Intelligence</h1>
  <p>AI-powered ICP analysis &amp; personalised email sequence generator with HubSpot sync</p>
</div>
""", unsafe_allow_html=True)

# ── Input Section ─────────────────────────────────────────────────────────────

col_a, col_b = st.columns([1, 1], gap="large")

with col_a:
    st.markdown('<div class="card-title">Your Product & ICP</div>', unsafe_allow_html=True)
    product_desc = st.text_area(
        "Product Description",
        height=130,
        placeholder="E.g. Acme is a revenue intelligence platform that helps B2B sales teams identify buying signals, prioritise outreach, and increase win rates by 30%.",
        help="Describe what your product does and its core value proposition.",
    )
    icp_criteria = st.text_area(
        "ICP Criteria",
        height=130,
        placeholder="E.g. Series B+ SaaS companies, 50-500 employees, US-based, revenue ops or sales leadership, using Salesforce, struggling with pipeline visibility.",
        help="Define your Ideal Customer Profile: firmographics, technographics, pain points.",
    )

with col_b:
    st.markdown('<div class="card-title">Target</div>', unsafe_allow_html=True)
    company_url = st.text_input(
        "Target Company URL",
        placeholder="https://www.acme.com",
        help="The company's website — Claude will infer context from the domain.",
    )
    st.markdown("")
    contact_name = st.text_input(
        "Contact Full Name",
        placeholder="Sarah Chen",
    )
    contact_role = st.text_input(
        "Contact Role / Title",
        placeholder="VP of Revenue Operations",
    )

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ── Analyse Button ────────────────────────────────────────────────────────────

can_run = all([product_desc, icp_criteria, company_url, contact_name, contact_role])

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
    if not product_desc:
        missing.append("Product Description")
    if not icp_criteria:
        missing.append("ICP Criteria")
    if not company_url:
        missing.append("Company URL")
    if not contact_name:
        missing.append("Contact Name")
    if not contact_role:
        missing.append("Contact Role")
    if missing:
        st.info(f"Complete to enable analysis: {' · '.join(missing)}", icon="ℹ️")

# ── Results ───────────────────────────────────────────────────────────────────

if run_btn and can_run:
    client = anthropic.Anthropic(api_key=anthropic_key)

    # ── ICP Analysis ──────────────────────────────────────────────────────────
    st.markdown("## ICP Fit Analysis")
    with st.spinner("Analyzing company-ICP fit…"):
        try:
            analysis = run_icp_analysis(client, product_desc, icp_criteria, company_url)
            st.session_state["analysis"] = analysis
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    analysis = st.session_state.get("analysis", {})
    score = analysis.get("score", 0)
    css_class = score_class(score)

    c1, c2 = st.columns([1, 2], gap="large")

    with c1:
        st.markdown(f"""
<div class="card" style="text-align:center;">
  <div class="card-title">ICP Fit Score</div>
  <div class="score-badge {css_class}">{score}</div>
  <div style="font-size:.75rem; color:#6b7280; margin-bottom:6px;">out of 10</div>
  <div style="font-size:1rem; font-weight:700; color:#1a1f36;">{analysis.get('verdict','—')}</div>
</div>
""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
<div class="card">
  <div class="card-title">Assessment</div>
  <p style="color:#374151; margin-bottom:14px;">{analysis.get('summary','')}</p>
  <div class="card-title">Strengths</div>
  <div style="margin-bottom:12px;">{''.join(f'<span class="chip">✓ {s}</span>' for s in analysis.get('strengths',[]))}</div>
  <div class="card-title">Gaps</div>
  <div>{''.join(f'<span class="chip" style="background:#fff1f2;color:#be123c;">✗ {g}</span>' for g in analysis.get('gaps',[]))}</div>
</div>
""", unsafe_allow_html=True)

    # Recommended angle
    angle = analysis.get("recommended_angle", "")
    st.markdown(f"""
<div class="card" style="background:#f0f4ff; border-color:#c7d2fe;">
  <div class="card-title" style="color:#4338ca;">🎯 Recommended Outreach Angle</div>
  <p style="color:#1e1b4b; font-size:.95rem; margin:0;">{angle}</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ── Email Sequence ─────────────────────────────────────────────────────────
    st.markdown("## 📧 Personalised 4-Email Sequence")
    with st.spinner("Generating outreach sequence…"):
        try:
            emails = run_sequence_generation(
                client, product_desc, icp_criteria, company_url,
                contact_name, contact_role, angle,
            )
            st.session_state["emails"] = emails
        except Exception as e:
            st.error(f"Sequence generation failed: {e}")
            st.stop()

    emails = st.session_state.get("emails", [])
    border_colors = ["#6366f1", "#8b5cf6", "#06b6d4", "#10b981"]

    for i, email in enumerate(emails):
        color = border_colors[i % len(border_colors)]
        send_date = (datetime.today() + timedelta(days=email.get("send_day", 1) - 1)).strftime("%b %d, %Y")

        st.markdown(f"""
<div class="email-card" style="border-left-color:{color};">
  <div class="email-seq">Email {email.get('sequence','')}</div>
  <div class="email-timing">⏱ {email.get('send_label','')} &nbsp;·&nbsp; Suggested send: {send_date}</div>
  <div class="email-subject">Subject: {email.get('subject','')}</div>
  <div class="email-body">{email.get('body','').replace('<','&lt;').replace('>','&gt;')}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ── HubSpot Sync ───────────────────────────────────────────────────────────
    st.markdown("## 🔶 HubSpot Integration")

    if not hubspot_key:
        st.warning("Add your HubSpot Private App Token in the sidebar to enable sync.", icon="🔑")
    else:
        st.markdown(f"""
<div class="hs-banner">
  <div style="font-size:2rem;">🔶</div>
  <div>
    <h3>Sync to HubSpot</h3>
    <p>Creates a contact record for <strong>{contact_name}</strong> at <strong>{company_url}</strong>
       and logs all 4 emails as Notes — ready to start your sequence.</p>
  </div>
</div>
""", unsafe_allow_html=True)

        hs_col, _ = st.columns([1, 3])
        with hs_col:
            hs_btn = st.button(
                "🔶 Push to HubSpot",
                type="secondary",
                use_container_width=True,
            )

        if hs_btn:
            with st.spinner("Syncing with HubSpot…"):
                log = push_to_hubspot(
                    hubspot_key,
                    contact_name,
                    contact_role,
                    company_url,
                    emails,
                )
            for icon, msg in log:
                if icon == "✅":
                    st.success(f"{icon} {msg}")
                else:
                    st.error(f"{icon} {msg}")

elif run_btn and not can_run:
    st.error("Please fill in all required fields and add your Anthropic API key.")
