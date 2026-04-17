# ─────────────────────────────────────────────────────────────────────────────
# GTM Outreach Intelligence Tool — V3
# Streamlit app: 3-stage gated workflow — account qualification, contact
# identification, email generation + export.  HubSpot CRM sync included.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import streamlit.components.v1 as components
import anthropic
import requests
import json
import re
import csv
import io
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
COMPANY_SIZES = [
    "1–10", "11–50", "51–200", "201–500",
    "501–1,000", "1,000–5,000", "5,000+"
]

INDUSTRIES = [
    "SaaS", "E-commerce", "Fintech", "Healthcare",
    "EdTech", "Enterprise Software", "MarTech", "HR Tech",
    "Cybersecurity", "Developer Tools / DevOps",
    "Real Estate / PropTech", "Legal Tech",
    "Supply Chain / Logistics", "Media & Publishing",
    "Climate Tech / CleanTech", "Professional Services",
    "Retail / Consumer", "Other"
]

LOCATIONS = [
    "US", "Canada", "UK", "Europe", "APAC",
    "Latin America", "Middle East & Africa",
    "Southeast Asia", "Global", "Other"
]

FUNDING_STAGES = [
    "Bootstrapped", "Pre-seed", "Seed",
    "Series A", "Series B", "Series C", "Series D+",
    "Growth Stage", "PE-backed", "Public", "Other"
]

TECH_STACK = [
    "Salesforce", "HubSpot", "Slack", "Zoom",
    "AWS", "Google Workspace", "Microsoft 365",
    "Outreach", "Salesloft", "Gong", "Marketo",
    "Snowflake", "Looker / Tableau", "Jira / Linear",
    "Other"
]

PAIN_POINTS = [
    "Pipeline visibility", "Revenue ops", "Sales efficiency",
    "Customer retention", "Data quality", "Lead generation",
    "Forecast accuracy", "Sales and marketing alignment",
    "Onboarding / time-to-value", "Churn reduction",
    "Pricing optimization", "Other"
]

SENIORITY_COLOURS = {
    "IC":          "#6366f1",
    "Manager":     "#8b5cf6",
    "Director":    "#06b6d4",
    "VP":          "#f59e0b",
    "C-Level":     "#ef4444",
}

# ── Email tone options ────────────────────────────────────────────────────────
# Each entry: (display label, description fed to Claude in the prompt)
TONES = {
    "Professional":          "formal, polished, and business-focused — confident but not pushy",
    "Casual & Friendly":     "warm, conversational, and approachable — like a message from a colleague",
    "Direct & No-Nonsense":  "terse, value-first, zero fluff — respect the reader's time above all",
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

  /* Context recap bar */
  .context-recap {
    background: #f0f4ff; border: 1px solid #c7d2fe; border-radius: 8px;
    padding: 10px 16px; font-size: .82rem; color: #3730a3;
    margin-bottom: 20px; font-weight: 600;
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
    industries_other: str,
    locations: list,
    locations_other: str,
    funding_stages: list,
    funding_other: str,
    tech_stack: list,
    tech_other: str,
    pain_points: list,
    pain_other: str,
    additional: str,
) -> str:
    """
    Assemble the structured ICP dropdown selections into a single human-readable
    string that can be passed directly into the Claude analysis prompt.
    """
    parts = []

    if company_size:
        parts.append(f"Company size: {company_size} employees")

    if industries:
        industry_list = [i for i in industries if i != "Other"]
        if industries_other:
            industry_list.append(industries_other)
        if industry_list:
            parts.append(f"Industry: {', '.join(industry_list)}")

    if locations:
        loc_list = [l for l in locations if l != "Other"]
        if locations_other:
            loc_list.append(locations_other)
        if loc_list:
            parts.append(f"Location: {', '.join(loc_list)}")

    if funding_stages:
        fund_list = [f for f in funding_stages if f != "Other"]
        if funding_other:
            fund_list.append(funding_other)
        if fund_list:
            parts.append(f"Funding stage: {', '.join(fund_list)}")

    if tech_stack:
        tech_list = [t for t in tech_stack if t != "Other"]
        if tech_other:
            tech_list.append(tech_other)
        if tech_list:
            parts.append(f"Uses: {', '.join(tech_list)}")

    if pain_points:
        pain_list = [p for p in pain_points if p != "Other"]
        if pain_other:
            pain_list.append(pain_other)
        if pain_list:
            parts.append(f"Key pain points: {', '.join(pain_list)}")

    if additional and additional.strip():
        parts.append(f"Additional context: {additional.strip()}")

    return "; ".join(parts) if parts else "No specific ICP criteria defined"


# ── CSV export helper ────────────────────────────────────────────────────────

def build_csv(emails: list, tone: str, contact_name: str, company_url: str) -> str:
    """
    Build a UTF-8 CSV string from the email sequence for st.download_button.
    Reads current widget states (subject_N, body_N, approve_N) so edits and
    approval decisions made in the Review step are reflected in the export.
    Returns the CSV as a plain string.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
    writer.writerow([
        "Email #", "Send Day", "Send Label", "Subject", "Body",
        "Tone", "Included", "Contact", "Company",
    ])
    for i, email in enumerate(emails):
        subject  = st.session_state.get(f"subject_{i}", email.get("subject", ""))
        body     = st.session_state.get(f"body_{i}",    email.get("body", ""))
        included = "Yes" if st.session_state.get(f"approve_{i}", True) else "No"
        writer.writerow([
            email.get("sequence", i + 1),
            email.get("send_day", ""),
            email.get("send_label", ""),
            subject,
            body,
            tone,
            included,
            contact_name,
            company_url,
        ])
    return buf.getvalue()


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


def run_linkedin_parse(client: anthropic.Anthropic, profile_text: str) -> dict:
    """
    Parse pasted LinkedIn profile text to extract structured contact info.
    Returns: name, title, company, hook (or None).
    """
    prompt = f"""Extract structured contact information from this LinkedIn profile page text.
Return ONLY valid JSON:
{{
  "name": "<full name>",
  "title": "<current job title>",
  "company": "<current company name>",
  "hook": "<one specific, concrete detail from their background that could personalize a cold email — e.g. 'recently promoted from Director to VP', 'previously at Salesforce', 'posted about scaling their RevOps team', 'company just raised Series B'. If nothing specific, return null.>"
}}

PROFILE TEXT:
{profile_text}"""

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
    tone: str = "Professional",
    hook: str = None,
) -> list:
    """
    Generate a 4-email cold outreach sequence.
    Returns list of dicts: sequence, send_day, send_label, subject, body.
    `tone` must be one of the keys in TONES; its description is injected into
    the prompt so Claude calibrates vocabulary, sentence length, and formality.
    Optional `hook` injects a personalization detail into Email 1.
    """
    first_name  = contact_name.strip().split()[0] if contact_name.strip() else "there"
    tone_desc   = TONES.get(tone, TONES["Professional"])
    hook_line   = (
        f"\nPERSONALIZATION HOOK (use this specific detail in Email 1 if relevant): {hook}"
        if hook else ""
    )

    prompt = f"""You are an elite B2B sales copywriter. Write a 4-email cold outreach sequence.

VENDOR PRODUCT: {product}
ICP CRITERIA: {icp}
TARGET COMPANY: {company_url}
CONTACT: {contact_name}, {contact_role}
LEADING ANGLE: {angle}
EMAIL TONE: {tone} — {tone_desc}{hook_line}

Guidelines:
- Email 1 (Day 1): Hyper-personalised opener, reference their company, one clear value prop, soft CTA
- Email 2 (Day 4): Concrete data point or insight relevant to their role, reply-to-thread CTA
- Email 3 (Day 9): Brief social proof / mini case study, direct ask for a call
- Email 4 (Day 17): Polite breakup email, leave door open, very short

Each email: under 150 words, tone MUST match "{tone}" throughout, NO "I hope this finds you well".
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


def hubspot_create_task(
    api_key: str, contact_id: str, seq: dict
) -> tuple:
    """
    Create a HubSpot Task for one email in the sequence.
    The task is due on the email's send_day (relative to today) and is
    associated with the contact via associationTypeId 216 (Task → Contact).

    Returns (success: bool, message: str).
    """
    due_dt = datetime.utcnow() + timedelta(days=seq.get("send_day", 1) - 1)
    payload = {
        "properties": {
            "hs_task_subject":  f"Send Email {seq['sequence']}: {seq['subject']}",
            "hs_task_body":     seq["body"],
            "hs_timestamp":     due_dt.isoformat() + "Z",   # task due date
            "hs_task_status":   "NOT_STARTED",
            "hs_task_type":     "EMAIL",
            "hs_task_priority": "MEDIUM",
        },
        "associations": [{
            "to":    {"id": contact_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 216}],
        }],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = requests.post("https://api.hubapi.com/crm/v3/objects/tasks",
                          headers=headers, json=payload, timeout=15)
        if r.status_code in (200, 201):
            return True, f"Email {seq['sequence']} task created (due {due_dt.strftime('%b %d')}, Task ID: {r.json().get('id','')})"
        return False, f"Task error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"Request failed: {e}"


def push_to_hubspot(
    api_key: str, contact_name: str, contact_role: str,
    company_url: str, emails: list
) -> list:
    """
    Create contact, then for each approved email:
      1. Log it as a Note (for history/activity feed)
      2. Create a Task (for to-do reminders with a due date)
    Returns [(icon, message), ...] log entries.
    """
    log = []
    ok, contact_id, msg = hubspot_create_contact(api_key, contact_name, contact_role, company_url)
    log.append(("✅" if ok else "❌", msg))
    if not ok:
        return log
    for email in emails:
        # Note — preserves the email body in the activity timeline
        e_ok, e_msg = hubspot_log_email_note(api_key, contact_id, email, contact_name)
        log.append(("✅" if e_ok else "❌", e_msg))
        # Task — creates a reminder with a due date matching the send_day
        t_ok, t_msg = hubspot_create_task(api_key, contact_id, email)
        log.append(("✅" if t_ok else "❌", t_msg))
    return log


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### How it works")
    st.markdown("""
1. **Qualify the account** — paste a company URL and score ICP fit
2. **See who to target** — Claude recommends the right role/seniority
3. **Add your contact** — name + title, or paste their LinkedIn profile
4. **Generate emails** — personalized 4-email sequence with tone control
5. **Export or sync** — CSV download or HubSpot CRM sync
""")
    st.divider()

    # ── Stage progress ────────────────────────────────────────────────────────
    _s1 = st.session_state.get("stage1_complete", False)
    _s2 = st.session_state.get("stage2_complete", False)
    _s3 = bool(st.session_state.get("emails"))

    st.markdown("### 🗺️ Progress")
    st.markdown(
        f'<div style="background:#f8f9fc;border:1px solid #e8ecf0;border-radius:10px;padding:14px 16px;margin-bottom:12px;">'
        f'<div style="font-size:.75rem;margin-bottom:6px;">{"✅" if _s1 else "🔒"} Stage 1: Account Qualified</div>'
        f'<div style="font-size:.75rem;margin-bottom:6px;">{"✅" if _s2 else "🔒"} Stage 2: Contact Added</div>'
        f'<div style="font-size:.75rem;">{"✅" if _s3 else "🔒"} Stage 3: Emails Ready</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Live session stats ────────────────────────────────────────────────────
    if st.session_state.get("analysis") and st.session_state.get("emails"):
        _a   = st.session_state["analysis"]
        _e   = st.session_state["emails"]
        _t   = st.session_state.get("_tone", "Professional")
        _cn  = st.session_state.get("_contact_name", "—")

        _approved = sum(
            1 for i in range(len(_e))
            if st.session_state.get(f"approve_{i}", True)
        )
        _score   = _a.get("score", 0)
        _verdict = _a.get("verdict", "")
        _cls     = score_class(_score)
        _colour  = {"score-high": "#22c55e", "score-medium": "#f59e0b", "score-low": "#ef4444"}.get(_cls, "#6b7280")

        st.markdown("### 📈 Session Stats")
        st.markdown(
            f'<div style="background:#f8f9fc;border:1px solid #e8ecf0;border-radius:10px;padding:14px 16px;">'
            f'<div style="font-size:.7rem;font-weight:700;color:#7c8db0;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px;">Current Analysis</div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
            f'<span style="font-size:.82rem;color:#374151;">ICP Score</span>'
            f'<span style="font-weight:700;color:{_colour};">{_score}/10 · {_verdict}</span>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
            f'<span style="font-size:.82rem;color:#374151;">Tone</span>'
            f'<span style="font-weight:600;color:#4338ca;">{_t}</span>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
            f'<span style="font-size:.82rem;color:#374151;">Emails approved</span>'
            f'<span style="font-weight:700;color:#1a1f36;">{_approved} / {len(_e)}</span>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;">'
            f'<span style="font-size:.82rem;color:#374151;">Contact</span>'
            f'<span style="font-weight:600;color:#1a1f36;font-size:.82rem;">{_cn}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.divider()

    st.caption("GTM Outreach Intelligence · V3")


# ── Hero ──────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <h1>🎯 GTM Outreach Intelligence <span class="v2-badge">V3</span></h1>
  <p>3-stage workflow: qualify the account → identify your contact → generate a personalised email sequence</p>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# TABBED LAYOUT
# Tab 1 ⚙️ Setup          — ICP form + company URL, qualify button
# Tab 2 🎯 Qualification   — ICP score, seniority advisor, proceed CTA
# Tab 3 👤 Contact         — contact input, LinkedIn paste, tone, generate
# Tab 4 📧 Emails + Export — review/approve, CSV download, HubSpot sync
#
# Button variables are initialised to False before the tab blocks so the
# handlers at the bottom can reference them safely regardless of gating.
# ═════════════════════════════════════════════════════════════════════════════

qualify_btn  = False
can_qualify  = False
generate_btn = False
can_generate = False

tab1, tab2, tab3, tab4 = st.tabs([
    "⚙️  Setup",
    "🎯  Qualification",
    "👤  Contact",
    "📧  Emails + Export",
])


# ── Tab 1: Setup ──────────────────────────────────────────────────────────────
with tab1:

    # ── SECTION A: Core Inputs ────────────────────────────────────────────────
    sec_a_left, sec_a_right = st.columns([1, 1], gap="large")

    with sec_a_left:
        st.markdown('<div class="card-title">Your Product</div>', unsafe_allow_html=True)
        product_desc = st.text_area(
            "Product Description",
            height=130,
            placeholder="E.g. Acme is a revenue intelligence platform that helps B2B sales teams identify buying signals, prioritise outreach, and increase win rates by 30%.",
            help="Describe your product's core value proposition.",
        )

    with sec_a_right:
        st.markdown('<div class="card-title">Target Company</div>', unsafe_allow_html=True)
        company_url = st.text_input(
            "Target Company URL",
            placeholder="https://www.acme.com",
            help="Claude infers company context from the domain.",
        )

    # ── SECTION B: ICP Criteria ───────────────────────────────────────────────
    st.markdown('<div class="icp-header">🎯 ICP Criteria</div>', unsafe_allow_html=True)

    sec_b_left, sec_b_right = st.columns([1, 1], gap="large")

    with sec_b_left:
        icp_size = st.selectbox(
            "Company Size", [""] + COMPANY_SIZES,
            format_func=lambda x: "Any size" if x == "" else x,
            help="Number of employees at the target company.",
        )

        icp_industries = st.multiselect(
            "Industry", INDUSTRIES,
            help="Select one or more industries that match your ICP.",
        )
        if "Other" in icp_industries:
            icp_industries_other = st.text_input(
                "Specify other industry",
                placeholder="e.g. Space Tech, Gaming, GovTech...",
                key="industry_other",
            )
        else:
            icp_industries_other = ""

        icp_location = st.multiselect(
            "Location", LOCATIONS,
            help="Select one or more regions.",
        )
        if "Other" in icp_location:
            icp_location_other = st.text_input(
                "Specify other location",
                placeholder="e.g. Sub-Saharan Africa, Central Asia...",
                key="location_other",
            )
        else:
            icp_location_other = ""

        icp_funding = st.multiselect(
            "Funding Stage", FUNDING_STAGES,
            help="Select one or more funding stages that match your ICP.",
        )
        if "Other" in icp_funding:
            icp_funding_other = st.text_input(
                "Specify other funding stage",
                placeholder="e.g. Corporate venture, Government-funded...",
                key="funding_other",
            )
        else:
            icp_funding_other = ""

    with sec_b_right:
        icp_tech = st.multiselect(
            "Tech Stack", TECH_STACK,
            help="Tools the ideal customer already uses.",
        )
        if "Other" in icp_tech:
            icp_tech_other = st.text_input(
                "Specify other tech",
                placeholder="e.g. Intercom, Segment, dbt...",
                key="tech_other",
            )
        else:
            icp_tech_other = ""

        icp_pain = st.multiselect(
            "Pain Points", PAIN_POINTS,
            help="Challenges your ICP is actively facing.",
        )
        if "Other" in icp_pain:
            icp_pain_other = st.text_input(
                "Specify other pain point",
                placeholder="e.g. Multi-product bundling, Territory conflicts...",
                key="pain_other",
            )
        else:
            icp_pain_other = ""

        icp_additional = st.text_area(
            "Additional ICP Details (optional)",
            height=90,
            placeholder=(
                "Anything else that defines your ideal customer — "
                "e.g. 'must have a dedicated sales team', "
                "'companies that recently hired a VP of Sales', "
                "'using a legacy CRM they want to replace'..."
            ),
            help="Free-form context that doesn't fit the dropdowns above. Claude will factor this in.",
        )

    # ── Assemble ICP string from dropdowns ────────────────────────────────────
    icp_string = build_icp_string(
        icp_size,
        icp_industries, icp_industries_other,
        icp_location, icp_location_other,
        icp_funding, icp_funding_other,
        icp_tech, icp_tech_other,
        icp_pain, icp_pain_other,
        icp_additional,
    )

    # ── SECTION C: Qualify button ─────────────────────────────────────────────
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    can_qualify = bool(product_desc.strip() and company_url.strip())

    run_col, _ = st.columns([1, 3])
    with run_col:
        qualify_btn = st.button(
            "⚡ Qualify This Account",
            type="primary",
            disabled=not can_qualify,
            use_container_width=True,
        )

    if not can_qualify:
        missing = []
        if not product_desc.strip(): missing.append("Product Description")
        if not company_url.strip():  missing.append("Company URL")
        if missing:
            st.info(f"Complete to enable analysis: {' · '.join(missing)}", icon="ℹ️")

    # Post-qualification indicator
    if st.session_state.get("stage1_complete"):
        _score   = st.session_state.get("analysis", {}).get("score", 0)
        _verdict = st.session_state.get("analysis", {}).get("verdict", "")
        st.success(
            f"✅ Account qualified — ICP score **{_score}/10** ({_verdict}). "
            "Switch to **🎯 Qualification** to see results and proceed.",
            icon="🎯",
        )


# ── Tab 2: Qualification ──────────────────────────────────────────────────────
with tab2:
    if not st.session_state.get("stage1_complete"):
        st.info(
            "Complete the **⚙️ Setup** tab and click **⚡ Qualify This Account** "
            "to see results here.",
            icon="📊",
        )
    else:
        analysis  = st.session_state["analysis"]
        seniority = st.session_state.get("seniority", {})

        score     = analysis.get("score", 0)
        css_class = score_class(score)
        angle     = analysis.get("recommended_angle", "")

        st.markdown("## 📊 ICP Fit Analysis")

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

        # ── Who to Target ─────────────────────────────────────────────────────
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
  <div class="card-title" style="color:#7c3aed;">🎯 Who to Target at This Company</div>
  <div style="margin-bottom:12px;">{primary_badge}{secondary_badge}</div>
  <p style="color:#374151;font-size:.875rem;margin:0;">{reasoning}</p>
</div>
""", unsafe_allow_html=True)

        # ── Proceed CTA ───────────────────────────────────────────────────────
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        proceed_col, _ = st.columns([2, 2])
        with proceed_col:
            if st.button(
                "→ I Found My Contact — Let's Write the Emails",
                type="primary",
                use_container_width=True,
                key="proceed_to_contact_btn",
            ):
                st.session_state["_goto_contact"] = True
                st.rerun()


# ── Tab 3: Contact ────────────────────────────────────────────────────────────
with tab3:
    if not st.session_state.get("stage1_complete"):
        st.info(
            "Complete account qualification first (**⚙️ Setup** tab).",
            icon="🔒",
        )
    else:
        # Context recap bar
        _recap_url      = st.session_state.get("_company_url", "—")
        _recap_score    = st.session_state.get("analysis", {}).get("score", "—")
        _recap_seniority = st.session_state.get("seniority", {}).get("primary_level", "—")
        st.markdown(
            f'<div class="context-recap">'
            f'Qualifying: {_recap_url} &nbsp;|&nbsp; '
            f'ICP Score: {_recap_score}/10 &nbsp;|&nbsp; '
            f'Target: {_recap_seniority}'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown("## 👤 Add Your Contact")

        # ── Option A: Manual entry ────────────────────────────────────────────
        st.markdown("#### Contact Details")
        m_col1, m_col2 = st.columns(2, gap="medium")
        with m_col1:
            contact_name_input = st.text_input(
                "Contact Name",
                placeholder="Sarah Chen",
                key="contact_name_field",
                value=st.session_state.get("_contact_name", ""),
            )
        with m_col2:
            contact_role_input = st.text_input(
                "Contact Title / Role",
                placeholder="VP of Revenue Operations",
                key="contact_role_field",
                value=st.session_state.get("_contact_role", ""),
            )

        # ── Option B: LinkedIn text paste ─────────────────────────────────────
        with st.expander("📋 Paste LinkedIn Profile (optional enrichment)"):
            st.markdown(
                "Go to their LinkedIn profile → select all text on the page "
                "(**Ctrl+A**) → paste it here. Claude will extract their name, "
                "title, and any relevant details to personalize the emails."
            )
            linkedin_text = st.text_area(
                "LinkedIn profile text",
                height=200,
                placeholder="Paste LinkedIn profile text here...",
                key="linkedin_paste_field",
                label_visibility="collapsed",
            )

        # Show auto-fill success if LinkedIn was previously parsed
        if st.session_state.get("_linkedin_parsed"):
            st.markdown(
                '<div class="linkedin-success">'
                '✓ Contact details auto-filled from LinkedIn profile. '
                'Hook extracted for email personalization.'
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        # ── Tone selector ─────────────────────────────────────────────────────
        st.markdown("### ✍️ Email Tone")
        tone_col, _ = st.columns([2, 1])
        with tone_col:
            email_tone = st.radio(
                "Choose the voice and style for your email sequence:",
                options=list(TONES.keys()),
                index=0,
                horizontal=True,
                key="email_tone",
                help=(
                    "Professional — polished and formal  |  "
                    "Casual & Friendly — warm and conversational  |  "
                    "Direct & No-Nonsense — terse, value-first"
                ),
            )
        st.caption(f"*{email_tone}:* {TONES[email_tone]}")

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        # ── Generate button ───────────────────────────────────────────────────
        contact_name = contact_name_input.strip()
        contact_role = contact_role_input.strip()
        can_generate = bool(contact_name and contact_role)

        gen_col, _ = st.columns([1, 3])
        with gen_col:
            generate_btn = st.button(
                "✉️ Generate Email Sequence",
                type="primary",
                disabled=not can_generate,
                use_container_width=True,
                key="generate_emails_btn",
            )

        if not can_generate:
            missing_contact = []
            if not contact_name: missing_contact.append("Contact Name")
            if not contact_role: missing_contact.append("Contact Title / Role")
            if missing_contact:
                st.info(
                    f"Required to generate emails: {' · '.join(missing_contact)}",
                    icon="ℹ️",
                )

        # Post-generation indicator
        if st.session_state.get("stage2_complete"):
            st.success(
                "✅ Email sequence generated — switch to **📧 Emails + Export** to review.",
                icon="📧",
            )


# ── Tab 4: Emails + Export ────────────────────────────────────────────────────
with tab4:
    if not st.session_state.get("stage2_complete"):
        st.info(
            "Generate your email sequence first (**👤 Contact** tab).",
            icon="🔒",
        )
    else:
        emails        = st.session_state["emails"]
        _tone         = st.session_state.get("_tone",         "Professional")
        _contact_name = st.session_state.get("_contact_name", "")
        _contact_role = st.session_state.get("_contact_role", "")
        _company_url  = st.session_state.get("_company_url",  "")

        # ── Email review ──────────────────────────────────────────────────────
        approved_count = sum(
            1 for i in range(len(emails))
            if st.session_state.get(f"approve_{i}", True)
        )

        st.markdown(
            f"## 📧 Review & Approve Email Sequence &nbsp;"
            f'<span style="font-size:.7rem;font-weight:700;letter-spacing:.08em;'
            f'text-transform:uppercase;background:#eef2ff;color:#4338ca;'
            f'border-radius:20px;padding:3px 12px;">✍️ {_tone}</span>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"**{approved_count} of {len(emails)} emails approved** for export/sync. "
            "Edit subjects/bodies inline, then uncheck any you want to exclude."
        )

        border_colors = ["#6366f1", "#8b5cf6", "#06b6d4", "#10b981"]

        for i, email in enumerate(emails):
            color     = border_colors[i % len(border_colors)]
            send_date = (datetime.today() + timedelta(days=email.get("send_day", 1) - 1)).strftime("%b %d, %Y")

            is_approved  = st.session_state.get(f"approve_{i}", True)
            card_opacity = "1" if is_approved else "0.45"
            card_border  = color if is_approved else "#d1d5db"

            st.markdown(
                f'<div style="border:1px solid {card_border};border-left:4px solid {card_border};'
                f'border-radius:10px;padding:18px 22px;margin-bottom:6px;'
                f'background:#fff;opacity:{card_opacity};transition:opacity .2s;">',
                unsafe_allow_html=True,
            )

            hdr_col, chk_col = st.columns([6, 1])
            with hdr_col:
                st.markdown(
                    f'<div class="email-seq">Email {email.get("sequence","")}</div>'
                    f'<div class="email-timing">⏱ {email.get("send_label","")} &nbsp;·&nbsp; Suggested send: {send_date}</div>',
                    unsafe_allow_html=True,
                )
            with chk_col:
                st.checkbox("Include", value=True, key=f"approve_{i}")

            st.text_input("Subject", value=email.get("subject", ""), key=f"subject_{i}")
            st.text_area("Body", value=email.get("body", ""), key=f"body_{i}", height=190)

            with st.expander("📋 Copy-ready text"):
                subj = st.session_state.get(f"subject_{i}", email.get("subject", ""))
                body = st.session_state.get(f"body_{i}",    email.get("body", ""))
                st.code(f"Subject: {subj}\n\n{body}", language=None)

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("")  # spacer

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        # ── CSV download ──────────────────────────────────────────────────────
        st.markdown("## 📥 Export Sequence")

        csv_data     = build_csv(emails, _tone, _contact_name, _company_url)
        csv_filename = (
            f"outreach_{_contact_name.replace(' ', '_')}_"
            f"{datetime.today().strftime('%Y%m%d')}.csv"
        )

        dl_col, _ = st.columns([1, 3])
        with dl_col:
            st.download_button(
                label="⬇️ Download as CSV",
                data=csv_data,
                file_name=csv_filename,
                mime="text/csv",
                use_container_width=True,
                help="Downloads all 4 emails with subject, body, send timing, tone, and approval status.",
            )
        st.caption(
            f"Includes all {len(emails)} emails with current edits and approval status. "
            "Import into Google Sheets, Excel, or your outreach tool."
        )

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        # ── HubSpot sync ──────────────────────────────────────────────────────
        st.markdown("## 🔶 HubSpot Integration *(optional)*")

        approved_emails = [
            {
                **emails[i],
                "subject": st.session_state.get(f"subject_{i}", emails[i]["subject"]),
                "body":    st.session_state.get(f"body_{i}",    emails[i]["body"]),
            }
            for i in range(len(emails))
            if st.session_state.get(f"approve_{i}", True)
        ]
        n_approved = len(approved_emails)

        st.markdown(f"""
<div class="hs-banner">
  <div style="font-size:2rem;">🔶</div>
  <div>
    <h3>Sync to HubSpot</h3>
    <p>Creates a contact for <strong>{_contact_name}</strong> at <strong>{_company_url}</strong>
       and logs <strong>{n_approved} approved email{'s' if n_approved != 1 else ''}</strong> as Notes + Tasks.</p>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown("""
<div class="card" style="background:#fff7f0;border-color:#fde8d8;margin-bottom:16px;">
  <div class="card-title" style="color:#c2500a;">🔑 Where to find your token</div>
  <p style="color:#374151;font-size:.875rem;margin:0;">
    <strong>Settings → Integrations → Private Apps</strong>.
    Needs <code>crm.objects.contacts.write</code>, <code>crm.objects.notes.write</code>
    and <code>crm.objects.tasks.write</code> scopes.<br><br>
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
            if n_approved == 0:
                st.warning(
                    "No emails are approved — tick at least one checkbox in the email list above.",
                    icon="⚠️",
                )
            else:
                hs_col, _ = st.columns([1, 3])
                with hs_col:
                    hs_btn = st.button(
                        f"🔶 Push {n_approved} Email{'s' if n_approved != 1 else ''} to HubSpot",
                        type="secondary",
                        use_container_width=True,
                        key="hs_push_btn",
                    )
                if hs_btn:
                    st.session_state.pop("hs_sync_log", None)
                    with st.spinner("Syncing with HubSpot…"):
                        sync_log = push_to_hubspot(
                            hs_token, _contact_name, _contact_role,
                            _company_url, approved_emails,
                        )
                    st.session_state["hs_sync_log"] = sync_log
        else:
            st.info("Enter your HubSpot API key above to enable CRM sync.", icon="ℹ️")

        if st.session_state.get("hs_sync_log"):
            st.markdown("**Sync results:**")
            for icon, msg in st.session_state["hs_sync_log"]:
                (st.success if icon == "✅" else st.error)(f"{icon} {msg}")


# ═════════════════════════════════════════════════════════════════════════════
# TAB SWITCH INJECTION
# If the proceed button was clicked, inject JS to click the Contact tab.
# Runs after all tab content has been rendered.
# ═════════════════════════════════════════════════════════════════════════════

if st.session_state.get("_goto_contact"):
    st.session_state.pop("_goto_contact")
    components.html("""
<script>
setTimeout(function() {
    var tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
    if (tabs.length > 2) { tabs[2].click(); }
}, 200);
</script>
""", height=0)


# ═════════════════════════════════════════════════════════════════════════════
# STAGE 1 HANDLER — Qualify This Account
# Runs ICP analysis + seniority advisor, stores results, sets stage1_complete.
# ═════════════════════════════════════════════════════════════════════════════

if qualify_btn and can_qualify:
    client = anthropic.Anthropic(api_key=anthropic_key)

    # Clear stale qualification results; preserve email state if re-qualifying
    for k in ("analysis", "seniority", "stage1_complete", "stage2_complete",
              "emails", "hs_sync_log", "_linkedin_parsed", "_hook"):
        st.session_state.pop(k, None)
    for k in list(st.session_state.keys()):
        if k.startswith(("approve_", "subject_", "body_")):
            st.session_state.pop(k, None)

    # Snapshot the inputs used for this qualification
    st.session_state["_product"]     = product_desc
    st.session_state["_icp_string"]  = icp_string
    st.session_state["_company_url"] = company_url

    # Step 1: ICP analysis
    with st.spinner("Analyzing company-ICP fit…"):
        try:
            analysis = run_icp_analysis(client, product_desc, icp_string, company_url)
            st.session_state["analysis"] = analysis
        except Exception as e:
            st.error(f"ICP analysis failed: {e}")
            st.stop()

    # Step 2: Seniority advisor (non-fatal)
    with st.spinner("Identifying optimal contact seniority…"):
        try:
            seniority = run_seniority_advisor(client, st.session_state["analysis"], product_desc)
            st.session_state["seniority"] = seniority
        except Exception as e:
            st.warning(f"Seniority advisor skipped: {e}")
            st.session_state["seniority"] = {}

    st.session_state["stage1_complete"] = True
    st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# STAGE 2 HANDLER — Generate Email Sequence
# Optionally parses LinkedIn text, then runs email generation.
# ═════════════════════════════════════════════════════════════════════════════

if generate_btn and can_generate:
    client = anthropic.Anthropic(api_key=anthropic_key)

    # Snapshot contact inputs
    st.session_state["_contact_name"] = contact_name
    st.session_state["_contact_role"] = contact_role
    st.session_state["_tone"]         = email_tone

    # Clear stale email state
    st.session_state.pop("emails", None)
    st.session_state.pop("hs_sync_log", None)
    st.session_state.pop("_hook", None)
    st.session_state.pop("_linkedin_parsed", None)
    for k in list(st.session_state.keys()):
        if k.startswith(("approve_", "subject_", "body_")):
            st.session_state.pop(k, None)

    # Step 1: LinkedIn parse (optional, if text was pasted)
    _raw_linkedin = st.session_state.get("linkedin_paste_field", "").strip()
    hook = None
    if _raw_linkedin:
        with st.spinner("Parsing LinkedIn profile…"):
            try:
                parsed = run_linkedin_parse(client, _raw_linkedin)
                # Auto-fill name/role if not already manually entered
                if parsed.get("name") and not contact_name:
                    st.session_state["_contact_name"] = parsed["name"]
                    contact_name = parsed["name"]
                if parsed.get("title") and not contact_role:
                    st.session_state["_contact_role"] = parsed["title"]
                    contact_role = parsed["title"]
                hook = parsed.get("hook") or None
                st.session_state["_hook"]           = hook
                st.session_state["_linkedin_parsed"] = True
            except Exception as e:
                st.warning(f"LinkedIn parse skipped: {e}")

    # Step 2: Email sequence generation
    _product    = st.session_state.get("_product",    product_desc)
    _icp_string = st.session_state.get("_icp_string", icp_string)
    _company    = st.session_state.get("_company_url", company_url)
    _angle      = st.session_state.get("analysis", {}).get("recommended_angle", "")

    with st.spinner("Generating personalised 4-email sequence…"):
        try:
            emails = run_sequence_generation(
                client, _product, _icp_string, _company,
                contact_name, contact_role, _angle,
                tone=email_tone,
                hook=hook,
            )
            st.session_state["emails"] = emails
        except Exception as e:
            st.error(f"Email generation failed: {e}")
            st.stop()

    st.session_state["stage2_complete"] = True
    st.rerun()
