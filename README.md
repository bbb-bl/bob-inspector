# BOB Inspector
### AI Construction Safety Inspector — ESADE PDAI 2026

> **BOB** (Building Observation Bot) is an AI-powered construction site safety inspection platform built for architects and site managers. It replaces paper-based inspection workflows with a real-time digital system: smart checklists, AI photo analysis, voice notes, and automated formal report generation.

**Tech stack:** Streamlit · Groq API (Llama 4 Scout) · Supabase · Python · ReportLab

---

## The Problem

A typical construction safety inspection without BOB:

| Step | Time |
|------|------|
| Print checklist, walk site | 45 min |
| Take photos (unlabelled) | 20 min |
| Type up findings back at office | 60 min |
| Email chain for sign-off | 24 hrs |
| File formal report | 30 min |

**Total: 2.5+ hours. 12+ manual steps. Reports delayed by 24 hours.**

BOB reduces this to **3 steps in under 30 minutes**.

---

## The Solution

```
Inspect → AI Analyses → Report Ready
```

1. **Inspect** — Walk the site, tick the smart checklist, upload photos
2. **AI Analyses** — BOB analyses every photo for safety hazards automatically
3. **Report** — One click generates a formal PDF report with regulation references

---

## Features

### Dashboard
- Project cards as collapsible expanders — active project expanded by default, others collapsed
- Colour-coded top accent bar per status (blue / green / amber / red) with status pill badge
- Active inspection panel inside each card — compliance %, progress bar, critical status
- Project brief per card — last inspection date, open findings, inspections conducted
- Report generation with PDF and Markdown download
- Photos auto-loaded from Supabase when generating report — no manual step required
- PDF embeds hazard photos with captions and red finding text
- Report history with timestamps per project
- Weekly progress comparison between two reports using AI
- Photo gallery — auto-loads current project's photos, switches on project change
- Hazard-only filter and description text search in gallery
- Add and delete projects (two-step confirmation)

### Inspection Tab
- Project selector — auto-sets checklist type based on building type (Commercial / Residential / Educational)
- Smart checklist sorted by severity (Critical first, checked items move to bottom)
- 45 checklist items sourced from RD 1627/1997
- Real-time checklist search — filters across all zones by text, zone, category
- Timestamp + inspector name recorded when each item is checked off
- History badges — amber pill showing how many previous visits an item was outstanding
- Before/After photo view — raw image on left, AI analysis result on right
- AI photo analysis via Llama 4 Scout vision model
- Collapsible photo sections (previous / newly uploaded / hazard summary)
- Voice notes with Wizard of Oz simulation (10 pre-written realistic transcriptions)
- Voice notes auto-classified by severity, can be added directly to checklist
- Custom checklist items
- Finish inspection flow with digital signature field

### Ask BOB (Chatbot)
- Multi-call tool_use architecture — BOB decides which tool to call based on the question
- 5 tools BOB can call autonomously:
  - get_checklist_summary — live checklist progress by zone
  - get_photo_hazards — detected hazards from photos
  - get_critical_findings — all critical outstanding items
  - lookup_regulation — searches RD 1627/1997 regulation database
  - generate_report_via_chat — triggers full report pipeline from chat
- Dynamic system prompt rebuilt every message with live inspection data
- Responds in the same language as the user (Spanish supported)
- Few-shot inspection note examples in system prompt

### Report Generation
- LLM prompt assembles all live session data: checklist, photos, voice notes
- 6-section formal report: Executive Summary, Critical Findings, Completed Checks, Outstanding Items, Recommendations, Next Steps
- Editable text area before download
- PDF download — styled with ReportLab (project header, section headings, red critical items, timestamp)
- Markdown download — for editing in Word or any text editor
- Plain text output — no markdown symbols in the text area
- Real inspection date injected automatically

---

## Architecture

```
app.py                          <- Entry point, BOB chatbot, tool_use logic, global CSS
components/
    inspection.py               <- Checklist, photo upload/analysis, voice notes
    dashboard.py                <- Project cards, report generation, photo gallery
utils/
    llm_utils.py                <- Shared Groq API wrapper (chat, describe_photo, generate_text)
    report.py                   <- Report prompt builder + LLM call
    report_pdf.py               <- ReportLab PDF generation
    severity.py                 <- Keyword classifier + CSV loader
    storage.py                  <- Supabase Storage integration
data/
    checklist.csv               <- 45 inspection items from RD 1627/1997
    projects.json               <- Barcelona fixture projects
    sample_inspection.json      <- Demo-ready inspection state for presentation
    voice_transcriptions.json   <- 10 pre-written Wizard of Oz voice notes
```

---

## Prototyping Strategies

| Feature | Strategy | Reason |
|---------|----------|--------|
| Voice notes | Wizard of Oz | Real STT requires browser microphone API not supported in Streamlit |
| GPS location | Hardcoded "Barcelona, Spain" | Mobile GPS permissions not available in Streamlit browser context |
| Photo storage | Supabase Storage | Persistent across sessions, no file system dependency on Streamlit Cloud |
| Report format | Markdown to PDF | Instant generation, no formatting bugs, opens in any editor |
| Severity classification | Keyword-based rules | No labelled training data; rule-based is explainable and auditable |

---

## Setup

### Local

```bash
git clone https://github.com/bbb-bl/bob-inspector.git
cd bob-inspector
pip install -r requirements.txt
```

Create .streamlit/secrets.toml:
```
GROQ_API_KEY = "your_groq_api_key"
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_key"
```

```bash
streamlit run app.py
```

### Streamlit Cloud

1. Connect repo to share.streamlit.io
2. Set secrets in the Streamlit Cloud dashboard (same keys as above)
3. Deploy — no additional configuration needed

---

## Demo Flow (Presentation)

1. Dashboard — project cards load with status badges and inspection briefs
2. Click Start inspection on Barceloneta Office Renovation
3. Active inspection panel appears inside the card — 62% compliance, 2 critical outstanding
4. Inspection tab — sample checklist (5/8 complete, 2 critical outstanding)
5. Upload photos — click Analyse with AI — before/after view appears
6. Press Start recording — Stop — voice note appears with severity badge
7. Dashboard — click Generate report with AI — photos auto-load, formal report appears
8. Click Download PDF — professional report with embedded hazard photos downloads instantly
9. Ask BOB tab — "What's still unchecked?" — BOB calls tool, returns live data

---

## Requirements

```
streamlit
pandas
Pillow
python-dotenv
openai
supabase
reportlab
matplotlib
```

---

BOB Inspector v1.0 — ESADE PDAI Final Project — April 2026

---

## Development Approach

BOB Inspector was built by a cross-functional team combining domain expertise in construction safety, AI engineering, and product design. The team independently designed the full product architecture, defined the inspection workflow, sourced and structured the RD 1627/1997 regulation dataset, and made all technical and UX decisions throughout development.

The team used Claude Code (Anthropic) as an AI coding assistant during implementation — primarily for accelerating boilerplate, debugging, and iterating on UI components. All core decisions — the tool-use architecture for BOB, the multi-modal hazard detection pipeline, the regulation grounding strategy to prevent hallucinations, the checklist data model, the Supabase integration, and the PDF generation pipeline — were designed and validated by the team.

The use of AI coding tools reflects the course's emphasis on prototyping as a discipline: leveraging available tools effectively to build a working, well-designed product in a constrained timeframe.

---

## Team

| Member | Role |
|--------|------|
| **Mohamed Aymen Elmezouari** | Dashboard, Report generation, PDF export, Data fixtures |
| **Botond Fazekas** | Tech lead, BOB chatbot, tool_use architecture, app skeleton |
| **Samreen Siddique** | Checklist data, Severity classifier, Inspection UI, Voice notes |
| **Eng Pongtanya** | LLM utils, Photo upload, AI photo analysis, Photo gallery |
