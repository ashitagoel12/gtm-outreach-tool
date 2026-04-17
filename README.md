# 🎯 GTM Outreach Intelligence Tool

> AI-powered 3-stage GTM workflow: qualify the account → identify your contact → generate a personalized email sequence.

**[Live Demo →](https://gtm-outreach-tool.streamlit.app)**

---

## What it does

Sales and GTM teams waste time writing cold emails to companies that aren't even worth targeting, or reaching out to the wrong person. V3 fixes the workflow order:

1. **Qualify the account first** — Claude scores the company's ICP fit (1–10), identifies strengths and gaps, and recommends the best outreach angle *before* you decide to pursue it.
2. **See who to target** — Claude recommends the right seniority level (IC → C-Level) based on the ICP fit and your product. Now you know *who* to find, not just *whether* to pursue.
3. **Add your contact** — Enter name + title manually, or paste their LinkedIn profile page and Claude extracts the details plus a personalization hook.
4. **Generate a 4-email sequence** — Fully personalized cold outreach (Day 1 → Day 17) tailored to the contact, company, recommended angle, and chosen tone.
5. **Review, export, or sync** — Edit inline, download as CSV, or push to HubSpot (contact + Notes + Tasks) with one click.

---

## Features — V3

| Feature | Description |
|---|---|
| 🎯 **Structured ICP Dropdowns** | Six dropdowns: company size, industry, location, funding stage, tech stack, pain points |
| 🧠 **ICP Fit Scoring** | Claude scores company fit 1–10 with verdict, strengths, gaps, and outreach angle |
| 💼 **Seniority Advisor** | Claude recommends primary + secondary seniority levels with reasoning — shown *before* you pick a contact |
| 📋 **LinkedIn Profile Parser** | Paste the full LinkedIn page text → Claude extracts name, title, and a personalization hook for Email 1 |
| ✍️ **Email Tone Selector** | Three tones: Professional / Casual & Friendly / Direct & No-Nonsense |
| ✉️ **4-Email Sequence** | Day 1 / 4 / 9 / 17 personalized emails with suggested send dates |
| 🔗 **Personalization Hook** | If a LinkedIn hook was extracted, Claude weaves it into Email 1 automatically |
| ✅ **Review & Approve** | Edit subject and body inline; check/uncheck emails before sync |
| 📋 **One-click Copy** | Copy-ready expander with subject + body in a single block per email |
| 📥 **CSV Export** | Download sequence with edits, approval status, tone, and contact metadata |
| 🔶 **HubSpot CRM Sync** | Creates contact + logs approved emails as Notes and dated Tasks |
| 🗺️ **Stage Progress** | Sidebar shows Stage 1 / 2 / 3 completion status at a glance |
| 🔒 **Gated Tabs** | Contact tab locked until account is qualified; Emails tab locked until sequence is generated |
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

> **HubSpot** uses a Personal Access Token you enter directly in the Emails + Export tab — no environment variable needed.

---

## How to use

| Step | Tab | Action |
|---|---|---|
| **1. Define ICP** | ⚙️ Setup | Choose company size, industry, location, funding stage, tech stack, and pain points |
| **2. Set target** | ⚙️ Setup | Paste company URL → click ⚡ Qualify This Account |
| **3. Review qualification** | 🎯 Qualification | See ICP score, strengths/gaps, outreach angle, and recommended seniority |
| **4. Proceed to contact** | 🎯 Qualification | Click "→ I Found My Contact" to jump to the Contact tab |
| **5. Add your contact** | 👤 Contact | Enter name + title manually, or paste their LinkedIn page text for auto-fill + hook |
| **6. Choose tone & generate** | 👤 Contact | Pick email tone → click ✉️ Generate Email Sequence |
| **7. Review & edit** | 📧 Emails + Export | Edit subjects/bodies inline; uncheck any to exclude |
| **8. Export or sync** | 📧 Emails + Export | Download as CSV, or enter HubSpot token and push approved emails as Notes + Tasks |

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
STAGE 1 — Account Qualification (⚙️ Setup tab)
  │
  ├─ Product description
  ├─ ICP dropdowns → build_icp_string()
  └─ Target company URL
        │
        ▼
  Claude Sonnet 4.5 (streaming)
        │
        ├─ [Call 1] ICP Fit Analysis
        │     └─ score, verdict, strengths, gaps, outreach angle
        │
        └─ [Call 2] Seniority Advisor
              └─ primary level, secondary level, reasoning
                    │
                    ▼ (🎯 Qualification tab — review + proceed)

STAGE 2 — Contact Identification (👤 Contact tab)
  │
  ├─ Manual: contact name + title
  └─ Optional: paste LinkedIn profile text
        │
        ▼
  [Call 3] LinkedIn Profile Parser (if text pasted)
        └─ name, title, personalization hook
              │
              ▼ (auto-fill fields; hook stored in session state)

STAGE 3 — Email Generation + Export (📧 Emails + Export tab)
  │
  ▼
  [Call 4] Email Sequence Generation (tone-aware, hook-aware)
        └─ 4 emails: Day 1 / 4 / 9 / 17
              │
              ▼ (review & edit)
        User approves / edits emails
              │
              ▼
        ┌─────────────────────────────┐
        │  CSV download (st.download) │
        │  HubSpot CRM API v3         │
        │  ├─ POST /contacts          │
        │  ├─ POST /notes  (×N)       │
        │  └─ POST /tasks  (×N)       │
        └─────────────────────────────┘
```

All Claude calls use `client.messages.stream()` to avoid timeouts. Results are stored in `st.session_state` with stage flags (`stage1_complete`, `stage2_complete`) that gate tab content and button availability.

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
