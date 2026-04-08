# 🎯 GTM Outreach Intelligence Tool

> AI-powered ICP analysis and personalized email sequence generator with HubSpot CRM integration.

**[Live Demo →](https://gtm-outreach-tool.streamlit.app)**

---

## What it does

Sales and GTM teams spend hours manually researching companies, scoring fit, and writing cold emails. This tool automates the entire workflow in under 60 seconds:

1. **Score ICP fit** — paste a company URL and Claude analyzes how well it matches your Ideal Customer Profile, returning a 1–10 score, strengths, gaps, and a recommended outreach angle.
2. **Generate a 4-email sequence** — Claude writes a fully personalized cold outreach sequence (Day 1 → Day 17) tailored to the contact's role and company context.
3. **Sync to HubSpot** — optionally create the contact record and log all 4 emails as Notes directly in your CRM with one click.

---

## Features

| Feature | Description |
|---|---|
| 🧠 **ICP Fit Scoring** | Claude scores target company fit 1–10 with verdict, strengths, gaps, and outreach angle |
| ✉️ **4-Email Sequence** | Personalized Day 1 / 4 / 9 / 17 emails with suggested send dates |
| 🔶 **HubSpot CRM Sync** | Creates contact + logs all 4 emails as Notes via HubSpot API v3 |
| 🔒 **Secure by default** | Anthropic key loaded from secrets; HubSpot token entered by the user at runtime |
| ⚡ **Streaming responses** | Claude streams output so there are no request timeouts |

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

# 3. Set up your environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Run the app
streamlit run app.py
```

### Environment variables

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

> HubSpot integration uses a token you enter directly in the app UI — no environment variable needed.

---

## How to use

| Step | Action |
|---|---|
| **1. Define context** | Enter your product description and ICP criteria in the left panel |
| **2. Set target** | Paste the company URL, contact name, and role in the right panel |
| **3. Analyze & generate** | Click ⚡ Analyze & Generate — Claude scores fit and writes 4 emails |
| **4. HubSpot sync (optional)** | Enter your HubSpot Personal Access Token and click 🔶 Push to HubSpot |

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
User Input
  │
  ├─ Product description + ICP criteria
  ├─ Target company URL
  └─ Contact name + role
        │
        ▼
  Claude Sonnet 4.5 (Anthropic API)
        │
        ├─ [Call 1] ICP Fit Analysis
        │     └─ Returns: score, verdict, strengths, gaps, outreach angle
        │
        └─ [Call 2] Email Sequence Generation
              └─ Returns: 4 personalized emails with send timing
                    │
                    ▼ (optional)
            HubSpot CRM API v3
                    │
                    ├─ POST /crm/v3/objects/contacts  → create contact
                    ├─ POST /crm/v3/objects/notes     → log email 1
                    ├─ POST /crm/v3/objects/notes     → log email 2
                    ├─ POST /crm/v3/objects/notes     → log email 3
                    └─ POST /crm/v3/objects/notes     → log email 4
```

Both Claude calls use streaming (`client.messages.stream`) to avoid HTTP timeouts on long responses. Claude is prompted to return strict JSON so responses can be parsed reliably without brittle text extraction.

---

## Security

- **Anthropic API key** — stored in Streamlit Cloud's secrets manager (`st.secrets`), never exposed in the UI or committed to the repository.
- **HubSpot Personal Access Token** — entered by the user at runtime in a password-masked input field. It is never stored server-side or persisted between sessions.
- Neither key is logged, printed, or written to disk at any point.

---

## Roadmap — V2

- [ ] **ICP dropdowns** — pre-built ICP templates by vertical (SaaS, fintech, healthcare) to speed up setup
- [ ] **Contact seniority advisor** — Claude suggests the right seniority level to target based on deal size and product type
- [ ] **Email tone refinement** — slider to adjust from formal to casual; option to match the company's public communication style
- [ ] **Google Sheets export** — one-click export of ICP scores and email sequences to a connected Sheet
- [ ] **Review & approve step** — edit emails inline before logging to HubSpot, instead of pushing immediately

---

## Why I built this

As an MBA operator, I spent hours manually researching companies for GTM outreach — reading about pages, scanning LinkedIn, piecing together whether a company was even worth targeting before writing a single word. This tool automates that entire workflow: from URL to CRM-ready outreach sequence in under a minute.

It's also a proof of concept that AI is a business lever, not just a tech toy. The value isn't in the model itself — it's in the workflow it unlocks and the GTM hours it gives back to operators.

---

## Author

**Ashita Goel** — [github.com/ashitagoel12](https://github.com/ashitagoel12)
