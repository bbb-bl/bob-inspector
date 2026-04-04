# BOB Inspector — Full Feature Breakdown

> AI Construction Safety Inspector · ESADE PDAI 2025

---

## Core Module 1 — Inspection Tab

### Project Management
- Select active project from dropdown (persists across reruns)
- Project auto-sets building type for the checklist
- Inspector name field stored in session for timestamped sign-offs

### Critical Items Banner
- Red alert appears at top when critical items are unresolved
- Lists item names inline so inspector sees them immediately

### Safety Checklist
- 45 pre-loaded items from RD 1627/1997 (Spanish construction regulation)
- Filtered by building type: Commercial / Residential / Educational
- Sorted by severity: Critical → Minor → Recommendation
- Grouped into zones (Electrical, Structural, Fire Safety, etc.)
- Each item has a severity badge (red / amber / blue)
- "Outstanding N visits" amber badge for recurring unresolved items (history tracking)
- Timestamp + inspector name recorded when each item is checked off
- Notes field per item with AI-powered severity reclassification
- Custom item input for ad-hoc findings

### Zone Navigation
- One-click jump buttons above checklist, one per zone
- Tooltip shows completion count per zone

### Checklist Search
- Real-time text filter across all zones
- Searches item text, zone name, category, and detail
- Flat results list with zone label, badges, full check/uncheck

### Site Photos
- Multi-photo upload (JPG, PNG)
- AI hazard detection per photo (Groq / LLaMA 4 Scout — multimodal vision)
- Before/after view: raw photo + AI analysis side by side
- Previous photos: collapsed thumbnail grid
- Newly uploaded photos: expanded with AI result
- Delete photo with two-step confirmation dialog
- Collapsible sections to reduce scroll

### Hazard Summary
- Collapsible section listing all flagged photos
- Thumbnail + location + timestamp + hazard description per photo

### Voice Notes
- Start/stop recording simulation
- Auto-transcription from pre-written field observations
- Severity badge per note (Critical / Minor / Recommendation)
- One-click "Add to Checklist" per voice note

### Finish Inspection Flow
- "Mark inspection as complete" button
- Summary card: Checklist %, Hazards found, Voice notes recorded
- Critical items still outstanding listed in red
- All critical resolved shown in green
- Inspector name + completion timestamp footer
- Digital signature field (typed name confirmation)
- "Start new inspection" reset button

---

## Core Module 2 — Dashboard Tab

### Project Cards
- Collapsible expanders — active project expanded by default, others collapsed
- Color-coded top accent bar per status (blue / green / amber / red)
- Status pill badge: IN PROGRESS / PENDING REVIEW / COMPLETE / ON HOLD
- Critical findings count in red badge
- Last inspection date, open findings count, total inspections
- "Start inspection →" primary button
- Delete project with two-step confirmation

### Report Generation
- AI-generated formal inspection report (6 sections)
- Sections: Executive Summary, Critical Findings, Completed Checks, Outstanding Items, Recommendations, Next Steps
- Photos auto-loaded from Supabase when report is generated — no manual step required
- Editable text area before download
- Persistent "Last saved at HH:MM" status label
- Download as PDF or Markdown

### PDF Report Contents
- Structured header: Project, Address, Type, Inspector, Date
- Full report body (plain text, section headings, bullet points)
- Critical items highlighted in red
- Photo Evidence section with embedded hazard photos (current project only)
- Caption per photo: filename, location, timestamp, hazard details
- Signature block: Inspector name, signed date, project
- Legal disclaimer line
- Generated-by footer

### Weekly Comparison
- Select any previous report to compare against current
- AI generates a Weekly Progress Summary (resolved / new / outstanding / trend)
- Download summary as Markdown

### Photo Gallery
- Auto-loads photos for the current project on dashboard render
- Switches automatically when a different project is selected
- Filter: hazards only
- Text search across AI descriptions
- Grid layout (3 columns)
- Expandable per photo with full description

---

## Core Module 3 — BOB Chatbot Tab

### Interface
- Header with "Ask BOB" + Clear chat / Export chat buttons right-aligned
- Welcome card with description
- Quick action buttons: Checklist status / List critical items / Summarize findings / Generate report
- Chat input at bottom
- Full conversation history display

### AI Capabilities (Tool-Use Architecture)
- BOB decides which tool to call based on the question (OpenAI-compatible function calling)
- `get_checklist_summary` — completion counts by zone, unchecked items
- `get_photo_hazards` — all uploaded photos and detected hazards
- `get_critical_findings` — critical unchecked items + hazard photos combined
- `lookup_regulation` — searches RD 1627/1997 regulation database by keyword
- `generate_report_via_chat` — triggers full report generation from chat

### BOB Behaviour
- Responds in the same language as the user
- Declines non-construction queries politely
- Always uses lookup tool for regulation questions (never guesses)
- Formal inspection note drafting on request
- Concise responses for questions, detailed for reports

### Chat Export
- Download full conversation as .txt transcript
- Auto-saves to project folder with timestamp

---

## Global Design System

### Visual
- Dark theme: `#0f0f1a` background, `#2855C8` brand blue
- Segmented control tabs (active = solid blue fill, full-width)
- Slim horizontal header with gradient accent line
- Two-tier typography: blue uppercase label + large section title
- Glass-card metrics with uppercase labels
- Color-coded expander indicators (red / green / blue lines)
- Dashed placeholder boxes for empty states

### UX
- Delete confirmations on all destructive actions
- Mobile-responsive CSS (44px touch targets, wrapping columns)
- Persistent project selection across page reruns
- Item history badges across inspection visits
- Timestamped checklist sign-offs
- Loading spinners on all AI and network calls

---

## AI Usage Summary

| Feature | Model | How |
|---|---|---|
| Photo hazard detection | LLaMA 4 Scout 17B (multimodal) | Base64 image + safety prompt → JSON response |
| Inspection report generation | LLaMA 4 Scout 17B | Structured prompt with all inspection data |
| BOB chatbot + tool-use | LLaMA 4 Scout 17B | OpenAI-compatible function calling — LLM selects tool |
| Weekly report comparison | LLaMA 4 Scout 17B | Two reports as context → progress summary |
| Severity reclassification | Rule-based (`severity.py`) | Keyword matching — no LLM call |
| Regulation lookup | Keyword search over static DB | Grounds LLM answers, prevents hallucination |

All LLM calls go through **Groq API** using the OpenAI SDK (`base_url="https://api.groq.com/openai/v1"`).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit (Python) |
| AI Model | Groq API — LLaMA 4 Scout 17B (text + vision) |
| Tool-Use | OpenAI-compatible function calling |
| Storage | Supabase (photo + description storage) |
| PDF Export | ReportLab |
| Hosting | Streamlit Community Cloud |
| Version Control | GitHub |

---

## Team

| Name | Role |
|---|---|
| Botond | AI / BOB chatbot, tool-use architecture, UI/UX overhaul |
| Samreen | Safety checklist, inspection logic |
| Eng | Photo upload, AI analysis, Supabase storage |
| Aymen | Dashboard, report generation, PDF export |

---

## Known Limitations

- Checklist state lost on page refresh (Streamlit session state only)
- Voice notes are simulated — no real microphone input
- No user authentication — inspector name is typed manually
- Single-user session — no multi-inspector collaboration
- Regulation database is static (RD 1627/1997 hardcoded)
- LLM output may hallucinate — reports require human review before legal use
- ~9 second load on project switch due to Supabase network fetch
