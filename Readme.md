# BanglaTruth 🔍
### Bangladesh's AI-Powered Fact-Checking & Misinformation Detection Platform
> বাংলাদেশের তথ্য যাচাই ও ভুল তথ্য শনাক্তকরণ প্ল্যাটফর্ম

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28-red)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-darkgreen)
![Groq](https://img.shields.io/badge/Groq-Llama3-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Overview

BanglaTruth is a production-grade, bilingual AI fact-checking platform designed specifically for the Bangladeshi information ecosystem. It addresses a critical gap — the lack of automated, AI-driven misinformation detection tools that understand both **English and Bangla** and are aware of Bangladeshi news sources, political context, and cultural nuance.

The platform uses a **multi-model jury architecture** — multiple large language models analyse the same claim independently and vote on a verdict. No single model decides alone. Disagreements are flagged as `CONTESTED`, giving users transparency into where uncertainty exists.

BanglaTruth is built for journalists, researchers, educators, and everyday citizens who need fast, reliable, and explainable fact-checking in their language.

---

## The Problem

Misinformation spreads rapidly in Bangladesh through:
- Facebook groups and pages with millions of followers
- WhatsApp forwards with no source attribution
- Parody news sites mimicking legitimate outlets
- Politically motivated fabricated quotes
- Out-of-context images and videos

Existing global fact-checking tools (Snopes, PolitiFact, AFP Fact Check) do not support Bangla, do not cover Bangladeshi news, and require manual human review. BanglaTruth automates the first layer of analysis — instantly, at scale, in both languages.

---

## Key Features

### 🤖 Multi-Model AI Jury
Multiple large language models run in **parallel** on every claim — not sequentially. Each model returns an independent verdict. A jury aggregation system counts votes and returns a final verdict. If models disagree, the claim is flagged as `CONTESTED` — a signal that the claim requires deeper investigation.

**Models in the jury:**
- Llama 3.3 (70B parameters) — primary reasoning model
- Llama 3.1 (8B parameters) — lightweight cross-check model

### 🌐 Full Bilingual Support
- Input in English → analysis and output in English
- Input in Bangla → analysis and output in Bangla
- Automatic language detection using `langdetect`
- No manual language selection required

### ⚖️ Structured Verdict System
Every claim receives one of five verdicts:

| Verdict | Meaning |
|---|---|
| ✅ TRUE | Claim is supported by evidence |
| ❌ FALSE | Claim is contradicted by evidence |
| ⚠️ MISLEADING | Claim contains partial truth but misleads |
| ❓ UNVERIFIED | Insufficient evidence to decide |
| ⚖️ CONTESTED | Models disagree — human review recommended |

### 🔬 Analysis Modes

**Quick Mode** — Fast analysis using standard prompting. Best for clear-cut claims.

**Deep Mode** — Chain-of-thought prompting. Each model first argues FOR the claim, then AGAINST it, then delivers a final verdict. More accurate for nuanced or politically sensitive claims.

**Reporter Mode** — Journalist-level output. Returns:
- Full explanation with citations
- Follow-up questions for further investigation
- Red flags and suspicious elements in the claim
- What a journalist should investigate next

### 🔗 Source Retrieval
- Automatically searches for relevant source links after every analysis
- Uses DuckDuckGo Search as primary engine
- Falls back gracefully if search fails
- Source links displayed alongside each model's verdict

### 🖼️ Related Image Search
- Finds visually relevant images for every claim
- Helps users quickly understand the context
- Uses DuckDuckGo Image Search

### 📰 Article URL Extraction
- Paste any news article URL
- App extracts the full article text automatically
- LLM identifies and surfaces the key claims
- User selects which claim to fact-check

### 👤 User Authentication
- Secure registration and login via Supabase Auth
- Email + password authentication
- Welcome email sent on registration
- Per-user session management
- Secure logout

### ☁️ Cloud Database
- Every fact-check saved to Supabase (PostgreSQL)
- Persistent history across sessions
- Queryable by user, verdict, timestamp

### 📊 Analytics Dashboard
- Personal fact-check history
- Verdict distribution chart
- Confidence trend over time
- Filter by verdict type

---

## Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                         USER                                     ║
║                  Browser / Mobile                                ║
╚══════════════════════════╦═══════════════════════════════════════╝
                           ║
                           ▼
╔══════════════════════════════════════════════════════════════════╗
║                    FRONTEND                                      ║
║              frontend_ui.py (Streamlit)                         ║
║                  Streamlit Cloud                                 ║
║                                                                  ║
║   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           ║
║   │  Fact Check │  │  Dashboard  │  │   Settings  │           ║
║   │    Page     │  │    Page     │  │    Page     │           ║
║   └─────────────┘  └─────────────┘  └─────────────┘           ║
╚══════════════════════════╦═══════════════════════════════════════╝
                           ║ HTTP REST API
                           ▼
╔══════════════════════════════════════════════════════════════════╗
║                     BACKEND                                      ║
║               backend_api.py (FastAPI)                          ║
║                    Render.com                                    ║
║                                                                  ║
║   ┌──────────────────────────────────────────────────────────┐  ║
║   │              PARALLEL LLM PROCESSING                     │  ║
║   │          asyncio.gather() — runs simultaneously          │  ║
║   │                                                          │  ║
║   │   ┌─────────────────┐    ┌─────────────────┐           │  ║
║   │   │  Llama 3.3 70B  │    │  Llama 3.1 8B   │           │  ║
║   │   │   (via Groq)    │    │   (via Groq)    │           │  ║
║   │   └────────┬────────┘    └────────┬────────┘           │  ║
║   │            │                      │                     │  ║
║   │            └──────────┬───────────┘                     │  ║
║   │                       ▼                                  │  ║
║   │            ┌─────────────────────┐                      │  ║
║   │            │  Jury Aggregation   │                      │  ║
║   │            │  Majority Voting    │                      │  ║
║   │            │  CONTESTED flagging │                      │  ║
║   │            └─────────────────────┘                      │  ║
║   └──────────────────────────────────────────────────────────┘  ║
║                                                                  ║
║   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ ║
║   │ DuckDuckGo   │  │  newspaper3k │  │     langdetect       │ ║
║   │ Search +     │  │  URL Article │  │  Language Detection  │ ║
║   │ Image Search │  │  Extraction  │  │   (55 languages)     │ ║
║   └──────────────┘  └──────────────┘  └──────────────────────┘ ║
╚══════════════════════════╦═══════════════════════════════════════╝
                           ║
                           ▼
╔══════════════════════════════════════════════════════════════════╗
║                     SUPABASE                                     ║
║                Europe (Frankfurt)                                ║
║                                                                  ║
║   ┌─────────────────────┐    ┌─────────────────────────────┐   ║
║   │   PostgreSQL DB      │    │        Auth Service         │   ║
║   │                      │    │                             │   ║
║   │  fact_checks table   │    │  Email + Password Login     │   ║
║   │  ├── id (uuid)       │    │  User Registration          │   ║
║   │  ├── username        │    │  Session Management         │   ║
║   │  ├── claim           │    │  Welcome Email              │   ║
║   │  ├── verdict         │    │                             │   ║
║   │  ├── confidence      │    └─────────────────────────────┘   ║
║   │  ├── explanation     │                                       ║
║   │  └── timestamp       │                                       ║
║   └─────────────────────┘                                        ║
╚══════════════════════════════════════════════════════════════════╝

Data Flow:
──────────
User submits claim
    → Frontend sends to Backend API
    → Backend runs Llama 3.3 + Llama 3.1 in parallel
    → Both models return verdict + confidence + explanation
    → Jury system aggregates votes → final verdict
    → DuckDuckGo search finds source links
    → DuckDuckGo image search finds related images
    → Result returned to Frontend
    → Frontend displays verdict card
    → Result saved to Supabase database
```




**Why two separate services?**

The backend runs AI inference asynchronously using Python's `asyncio`. Both models run at the same time — not one after the other. This makes every fact-check approximately 40% faster than sequential processing. Separating frontend and backend also means each can be scaled, updated, and deployed independently.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Streamlit | User interface |
| Backend | FastAPI + Uvicorn | REST API, async processing |
| AI Models | Groq API | LLM inference (Llama 3.3, 3.1) |
| Database | Supabase PostgreSQL | Persistent storage |
| Auth | Supabase Auth | User authentication |
| Search | DuckDuckGo Search | Source link retrieval |
| Images | DuckDuckGo Images | Visual context |
| Article Extraction | newspaper3k | URL content parsing |
| Language Detection | langdetect | Auto-detect English/Bangla |
| Data Processing | pandas | Dashboard analytics |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check — returns version and status |
| POST | `/fact-check` | Main fact-checking endpoint |
| POST | `/analyze-article` | Extract claims from a URL |
| GET | `/search` | Direct web search |
| GET | `/images` | Image search for a query |
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login existing user |
| POST | `/auth/logout` | Logout current user |

### Example Request
```json
POST /fact-check
{
    "claim": "The Bangladesh government signed a 99-year lease for Chittagong port with India",
    "deep": true,
    "reporter": false,
    "engine": "duckduckgo",
    "selected_model": "both",
    "lang_code": "en"
}
```

### Example Response
```json
{
    "final_verdict": "FALSE",
    "avg_confidence": 94,
    "individual": [
        {
            "model_name": "Llama 3.3",
            "verdict": "FALSE",
            "confidence": 95,
            "explanation": "No credible evidence exists...",
            "source": "Prothom Alo, The Daily Star"
        },
        {
            "model_name": "Llama 3.1",
            "verdict": "FALSE",
            "confidence": 93,
            "explanation": "Official government sources...",
            "source": "Bangladesh Government Press Office"
        }
    ],
    "source_links": [
        "https://www.thedailystar.net/...",
        "https://www.prothomalo.com/..."
    ]
}
```

---

## Local Setup

### Prerequisites
- Python 3.10+
- Groq API key (free at console.groq.com)
- Supabase account (free at supabase.com)

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/banglatruth.git
cd banglatruth

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:
```env
# Required
GROQ_API_KEY=your_groq_api_key

# Supabase
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Optional — Google Search (falls back to DuckDuckGo if not set)
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CX=your_google_custom_search_engine_id

# Deployment
PORT=8000
BACKEND_URL=http://localhost:8000
```

### Running Locally
```bash
# Terminal 1 — Start the backend
python backend_api.py
# API running at http://localhost:8000
# Docs available at http://localhost:8000/docs

# Terminal 2 — Start the frontend
streamlit run frontend_ui.py
# App running at http://localhost:8501
```

---

## Deployment

| Service | Platform | Cost |
|---|---|---|
| Frontend | Streamlit Cloud | Free |
| Backend | Render.com | Free tier |
| Database | Supabase | Free tier |

Total monthly cost at current scale: **$0**

---

## Performance

| Metric | Value |
|---|---|
| Average fact-check time | ~12 seconds |
| Sequential processing (old) | ~20 seconds |
| Parallel processing (current) | ~12 seconds |
| Speed improvement | ~40% faster |
| API uptime | 99.9% (with fallbacks) |
| Supported languages | English, Bangla + 53 others |

---

## Roadmap — Features Under Active Development

### 🧠 Expanding the AI Jury
Adding more models to the jury for higher accuracy and reduced bias. Planned additions include Mistral, Gemma 2, and DeepSeek R1 when stable JSON output is confirmed. More diverse models = more reliable verdicts.

### 🎯 Hallucination Comparison & Accuracy Scoring
Each model will be scored on how often it hallucinates — invents facts not in its training data. We will build a hallucination rate tracker that compares models over time and surfaces which model is most reliable for Bangladeshi political claims vs health claims vs economic claims.

### 🖼️ Image Processing & Visual Misinformation Detection
One of the most critical features for Bangladesh — detecting manipulated or out-of-context images. Planned features:
- Upload an image directly to BanglaTruth
- Reverse image search to find original source
- AI analysis of whether image matches the claim it accompanies
- Detection of common image manipulation artifacts

### 📊 Claim Credibility Timeline
Track how a claim's credibility changes over time as more evidence emerges. A claim marked UNVERIFIED today may become FALSE next week when new reporting surfaces.

### 🗺️ Misinformation Heat Map
Visualise which types of claims are being checked most — by category (politics, health, economy, religion) and by time period. Useful for researchers and journalists tracking misinformation trends.

### 🔄 Cross-Platform Monitoring
Automatic scanning of Bangladeshi Facebook pages, news sites, and Twitter/X accounts for emerging claims — before they go viral.


## Known Limitations

- AI models have a training knowledge cutoff — very recent events may return UNVERIFIED
- DuckDuckGo image search is rate-limited — images may not always load
- Google Custom Search API has a 100 queries/day free limit
- Models occasionally return inconsistent JSON — handled by 4-layer robust parsing

---

## Contributing

Contributions are welcome. Areas where help is most needed:
- Bangla NLP improvements
- Additional Bangladeshi news source integrations
- Unit test coverage
- Mobile UI improvements

Please open an issue before submitting a pull request.

---

## License

MIT License. See `LICENSE` for details.

---

## Built By

**Dante** — Built as a portfolio project and practical tool for the Bangladeshi information ecosystem.

Demonstrates:
- Async parallel AI inference with FastAPI
- Multi-model jury voting architecture
- Bilingual NLP pipeline
- Full-stack deployment (Streamlit + FastAPI + Supabase)
- Production-grade error handling and fallback systems

---

> *BanglaTruth — Because truth matters.*
> *সত্য গুরুত্বপূর্ণ।*