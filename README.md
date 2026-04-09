# 🎯 GTM Outreach Intelligence Tool

> AI-powered ICP analysis, seniority advisor, and personalized email sequence generator with HubSpot CRM integration.

**[Live Demo →](https://gtm-outreach-tool.streamlit.app)**

---

## What it does

Sales and GTM teams spend hours manually researching companies, scoring fit, and writing cold emails. This tool automates the entire workflow in under 60 seconds:

1. **Score ICP fit** — Claude analyzes a target company URL against your structured ICP criteria, returning a 1–10 score, strengths, gaps, and a recommended outreach angle.
2. **Advise on seniority** — Claude recommends the right seniority level (IC → C-Level) to target based on the ICP fit and your product.
3. **Generate a 4-email sequence** — fully personalized cold outreach (Day 1 → Day 17) tailored to the contact's role, company, and chosen tone.
4. **Review & edit** — edit subjects and bodies inline, approve or exclude individual emails before pushing.
5. **Export** — download the sequence as a CSV or sync to HubSpot (contact + Notes + Tasks) with one click.

---

## Features — V2

| Feature | Description |
|---|---|
| 🎯 **Structured ICP Dropdowns** | Six dropdowns: company size, industry, location, funding stage, tech stack, pain points |
| 🧠 **ICP Fit Scoring** | Claude scores company fit 1–10 with verdict, strengths, gaps, and outreach angle |
| 💼 **Seniority Advisor** | Claude recommends primary + secondary seniority levels with reasoning |
| 🔗 **LinkedIn Enrichment** | Auto-extract contact name from a LinkedIn profile URL (Apollo/Clay in V3) |
| ✍️ **Email Tone Selector** | Three tones: Professional / Casual & Friendly / Direct & No-Nonsense |
| ✉️ **4-Email Sequence** | Day 1 / 4 / 9 / 17 personalized emails with suggested send dates |
| ✅ **Review & Approve** | Edit subject and body inline; check/uncheck emails before sync |
| 📋 **One-click Copy** | Copy-ready expander with subject + body in a single block per email |
| 📥 **CSV Export** | Download sequence with edits, approval status, tone, and contact metadata |
| 🔶 **HubSpot CRM Sync** | Creates contact + logs approved emails as Notes and dated Tasks |
| 📊 **Tabs Layout** | ⚙️ Setup · 📊 Analysis · 📧 Emails · 📤 Export |
| 📈 **Live Sidebar Stats** | ICP score, tone, approved count, and contact name — updates in real time |
| 🔒 **Secure by default** | Anthropic key from secrets; HubSpot token entered at runtime, never stored |

---

## Quick start

### Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/ashitagoel12/gtm-outreach-tool.git
cd gtm-outreach-tool

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Run
streamlit run app.py
```

### Environment variables

```bash
# .env (local dev only — never commit this file)
ANTHROPIC_API_KEY=sk-ant-...
```

> **HubSpot** uses a Personal Access Token you enter directly in the Export tab — no environment variable needed.

---

## How to use

| Step | Tab | Action |
|---|---|---|
| **1. Define ICP** | ⚙️ Setup | Choose company size, industry, location, funding stage, tech stack, and pain points from the dropdowns |
| **2. Set target** | ⚙️ Setup | Paste company URL; enter contact name (or a LinkedIn URL) and role |
| **3. Pick tone** | ⚙️ Setup | Choose Professional, Casual & Friendly, or Direct & No-Nonsense |
| **4. Analyze** | ⚙️ Setup | Click ⚡ Analyze & Generate — Claude runs ICP analysis, seniority advisor, and email generation |
| **5. Review score** | 📊 Analysis | See ICP fit score, strengths/gaps chips, outreach angle, and recommended seniority level |
| **6. Edit emails** | 📧 Emails | Edit subjects and bodies inline; uncheck any you want to exclude |
| **7. Export or sync** | 📤 Export | Download as CSV, or enter your HubSpot token and push approved emails as Notes + Tasks |

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | [Streamlit](https://streamlit.io) |
| AI model | [Claude Sonnet 4.5](https://anthropic.com) via Anthropic Python SDK |
| CRM integration | [HubSpot CRM API v3](https://developers.hubspot.com/docs/api/overview) |
| Language | Python 3.10+ |
| Deployment | [Streamlit Cloud](https://share.streamlit.io) |

---

## Architecture

```
User Input (⚙️ Setup tab)
  │
  ├─ Product description
  ├─ ICP dropdowns → build_icp_string()
  ├─ Target company URL + contact
  └─ Email tone
        │
        ▼
  Claude Sonnet 4.5 (streaming)
        │
        ├─ [Call 1] ICP Fit Analysis
        │     └─ score, verdict, strengths, gaps, outreach angle
        │
        ├─ [Call 2] Seniority Advisor
        │     └─ primary level, secondary level, reasoning
        │
        └─ [Call 3] Email Sequence Generation (tone-aware)
              └─ 4 emails: Day 1 / 4 / 9 / 17
                    │
                    ▼ (📧 Emails tab — review & edit)
              User approves / edits emails
                    │
                    ▼ (📤 Export tab)
              ┌─────────────────────────────┐
              │  CSV download (st.download) │
              │  HubSpot CRM API v3         │
              │  ├─ POST /contacts          │
              │  ├─ POST /notes  (×N)       │
              │  └─ POST /tasks  (×N)       │
              └─────────────────────────────┘
```

All Claude calls use `client.messages.stream()` to avoid timeouts. Results are stored in `st.session_state` so the two-block pattern (execute once on click, render on every rerun) keeps the UI stable across widget interactions.

---

## Security

- **Anthropic API key** — stored in Streamlit Cloud secrets (`st.secrets`), never in the UI or the repo.
- **HubSpot Personal Access Token** — entered at runtime in a password-masked field; never stored server-side or persisted between sessions.
- Neither key is logged, printed, or written to disk.

---

## Why I built this

As an MBA operator, I spent hours manually researching companies for GTM outreach — reading about pages, scanning LinkedIn, piecing together whether a company was even worth targeting before writing a single word. This tool automates that entire workflow: from URL to CRM-ready outreach sequence in under a minute.

It's also a proof of concept that AI is a business lever, not just a tech toy. The value isn't in the model — it's in the workflow it unlocks and the GTM hours it gives back to operators.

---

## Author

**Ashita Goel** — [github.com/ashitagoel12](https://github.com/ashitagoel12)
