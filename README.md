# Taste Toronto

A natural-language restaurant discovery app for the Greater Toronto Area. Ask anything — "cozy Korean date night for 2 under $60", "hidden gem with a patio in Kensington", "family dim sum spot in Scarborough" — and get ranked recommendations with photos, a Google Maps view, and direct links.

![Taste Toronto](https://img.shields.io/badge/stack-Next.js%20%2B%20FastAPI-black)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![TypeScript](https://img.shields.io/badge/typescript-5.x-blue)

---

## How it works

Each message runs through a 4-node LangGraph pipeline:

```
User message
  → Intent Extractor   (GPT-4o)  — extracts occasion, group size, budget, cuisine, vibe
  → Retriever          (ChromaDB) — semantic vector search across 200 Toronto restaurants
  → Scoring Agent      (GPT-4o)  — ranks candidates against the specific request
  → Response Generator (GPT-4o)  — writes a 1-2 sentence opinionated intro
```

If the intent is incomplete (missing group size or budget), the pipeline short-circuits and asks a single follow-up question before retrieving.

---

## Features

- **Natural language queries** — any occasion, cuisine, vibe, neighborhood, or budget phrasing
- **Semantic search** — OpenAI embeddings + ChromaDB cosine similarity
- **GPT-4o scoring** — occasion fit, cuisine match, budget, group size, neighborhood proximity
- **Restaurant photos** — proxied from Google Places API, cached in-browser
- **Interactive map** — toggleable Google Maps panel with numbered rating markers
- **Conversation memory** — context carries across follow-up turns per session
- **Google Maps links** — direct place links on every card
- **Autocomplete** — Google Places autocomplete for neighborhood/restaurant search

---

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15, TypeScript, `@vis.gl/react-google-maps` |
| Backend | FastAPI, Python 3.11 |
| AI pipeline | LangGraph, OpenAI GPT-4o, `text-embedding-3-small` |
| Vector search | ChromaDB (persistent, local) |
| Database | SQLite (202 curated Toronto restaurants) |
| Maps & Photos | Google Places API (New), Google Maps JavaScript API |

---

## Project structure

```
Taste Toronto/
├── backend/
│   ├── main.py                    # FastAPI app + routes
│   ├── graph.py                   # LangGraph StateGraph
│   ├── agents/
│   │   ├── intent_extractor.py    # Message → structured intent
│   │   ├── restaurant_retriever.py# Intent → candidates via ChromaDB
│   │   ├── scoring_agent.py       # Candidates → ranked top 5
│   │   └── response_generator.py  # Ranked list → natural language
│   ├── db/
│   │   ├── models.py              # SQLite schema + migrations
│   │   ├── restaurant_repo.py     # DB queries
│   │   └── chroma_client.py       # ChromaDB client
│   ├── data/
│   │   ├── fetch_restaurants.py   # Seed script: Places API → SQLite + ChromaDB
│   │   └── enrich_geo_photo.py    # One-time: add lat/lng + photo_name to DB
│   ├── models/                    # Pydantic models
│   ├── services/
│   │   └── openai_client.py       # OpenAI singleton
│   └── conversation/
│       └── memory.py              # In-memory session store
│
├── frontend/
│   ├── app/                       # Next.js App Router
│   ├── components/
│   │   ├── ChatShell.tsx          # Main layout + map toggle state
│   │   ├── MessageBubble.tsx      # User/AI message rendering
│   │   ├── RestaurantCard.tsx     # Photo + metadata + links
│   │   ├── MapPanel.tsx           # Google Maps with rating markers
│   │   ├── ChatInput.tsx          # Rotating placeholder input
│   │   ├── FollowUpChips.tsx      # Suggested reply pills
│   │   ├── LocationSearch.tsx     # Neighborhood autocomplete
│   │   └── TypingIndicator.tsx    # Animated dots
│   ├── hooks/
│   │   ├── useChat.ts             # Message state + send/reset
│   │   └── useSession.ts          # UUID session from localStorage
│   └── lib/
│       ├── api.ts                 # Fetch wrappers
│       └── types.ts               # TypeScript mirrors of Pydantic models
│
├── start.bat                      # One-command startup (Windows)
└── .env                           # API keys (not committed)
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key
- Google Cloud project with **Places API (New)** and **Maps JavaScript API** enabled

### 1. Clone and configure

```bash
git clone https://github.com/WoodyChang21/Taste-Toronto.git
cd "Taste Toronto"
```

Create `.env` in the project root:

```env
OPENAI_API_KEY=sk-...
GOOGLE_PLACES_API_KEY=AIza...
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_GOOGLE_MAPS_KEY=AIza...
```

### 2. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Seed the database

Fetch 200 Toronto restaurants from Google Places, enrich with GPT-4o, and store in SQLite + ChromaDB:

```bash
cd "Taste Toronto"
python -m backend.data.fetch_restaurants
```

Then enrich with coordinates and photo references (~$3.50 one-time Google Places cost):

```bash
python -m backend.data.enrich_geo_photo
```

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

### 5. Start both servers

```bash
# Backend (port 8001)
cd "Taste Toronto"
uvicorn backend.main:app --port 8001

# Frontend (port 3000)
cd frontend
npm run dev
```

Or use the included `start.bat` on Windows.

Open [http://localhost:3000](http://localhost:3000).

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Main chat endpoint |
| `GET` | `/api/photo/{id}` | Proxied restaurant photo |
| `POST` | `/api/autocomplete` | Google Places autocomplete proxy |
| `GET` | `/api/health` | Health check |
| `DELETE` | `/api/session/{id}` | Clear conversation history |

---

## Data

The database contains 202 curated Toronto restaurants across Downtown, Yorkville, Kensington Market, Distillery District, Leslieville, Scarborough, and North York. Each record includes:

- Name, address, neighborhood, cuisine, price range
- Rating, review count, phone, website, reservation URL
- `semantic_tags` — 20+ descriptors (romantic, hidden_gem, patio, late_night, etc.)
- `occasion_scores` — 0–100 scores for date_night, birthday, family_gathering, hidden_gem
- `description` — 2-3 sentence GPT-4o summary
- `latitude`, `longitude` — for map markers
- `photo_name` — Google Places photo reference

---

## Cost estimate

| Item | Cost |
|---|---|
| DB seeding (one-time, 200 restaurants) | ~$15 |
| Photo + geo enrichment (one-time) | ~$3.50 |
| Per conversation (GPT-4o × 3 calls) | ~$0.03 |
| Per conversation (Google Places photo × 5) | ~$0.04 |
| Maps JS API per session | ~$0.007 |

---

## License

MIT
