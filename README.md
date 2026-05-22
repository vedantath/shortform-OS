# AVCOS

**Autonomous Viral Content Operating System**

An AI-powered pipeline that autonomously detects viral trends, generates short-form video scripts, synthesizes narration, assembles stock footage, and publishes to YouTube Shorts — with zero manual editing.

---

## How It Works

```
Google Trends / Reddit / YouTube RSS
           ↓
    Opportunity Scorer         (filters by score ≥ 70)
           ↓
    Claude Script Generator    (structured 60s script)
           ↓
    ElevenLabs Voice Synth     (narration + word timestamps)
           ↓
    Pexels / Pixabay Footage   (semantic keyword matching)
           ↓
    FFmpeg Composition         (1080×1920 MP4 + captions)
           ↓
    YouTube Data API v3        (scheduled upload)
           ↓
    YouTube Analytics API      (performance data → T+48h)
```

Every stage runs as an async Celery worker. The pipeline is non-blocking, retryable, and observable.

---

## Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Backend    | Python 3.11 + FastAPI                   |
| Queue      | Celery 5 + Redis 7                      |
| Database   | PostgreSQL 15                           |
| LLM        | Anthropic Claude API + OpenAI (fallback)|
| TTS        | ElevenLabs API                          |
| Footage    | Pexels API + Pixabay API                |
| Rendering  | FFmpeg 6 (CPU)                          |
| Publishing | YouTube Data API v3                     |
| Dashboard  | Next.js 14 + Tailwind CSS               |
| Deploy     | Docker + Docker Compose                 |

---

## Prerequisites

- Docker + Docker Compose V2
- API keys for: Anthropic, ElevenLabs, Pexels, Pixabay, YouTube OAuth 2.0
- (Optional) OpenAI API key for LLM fallback

---

## Quick Start

**1. Clone and configure**

```bash
git clone https://github.com/your-org/avcos.git
cd avcos
cp .env.example .env
# Fill in all API keys in .env
```

**2. Start the stack**

```bash
docker compose up -d
```

This starts: FastAPI backend, Celery workers (trend / script / render / upload / analytics), Redis, PostgreSQL, Next.js dashboard, and Flower queue monitor.

**3. Run database migrations**

```bash
docker compose exec backend alembic upgrade head
```

**4. Verify everything is running**

```bash
docker compose ps
# All services should show "Up"

docker compose exec backend celery -A app.core.celery inspect active
# Should show connected workers
```

**5. Open the dashboard**

- Pipeline dashboard: http://localhost:3000
- Celery Flower monitor: http://localhost:5555
- FastAPI docs: http://localhost:8000/docs

---

## Running the Pipeline

**Automatic (scheduled):**

The trend scraper runs every 30 minutes via Celery Beat. Any trend scoring ≥ 70 automatically triggers the full pipeline.

**Manual trigger:**

```bash
# Run a single pipeline cycle immediately
docker compose exec backend python -m app.cli run-pipeline

# Trigger from a specific trend ID
docker compose exec backend python -m app.cli run-pipeline --trend-id <uuid>

# Scrape trends only (no video generation)
docker compose exec backend python -m app.cli scrape-trends
```

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in values.

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (script generation) |
| `OPENAI_API_KEY` | OpenAI fallback key |
| `ELEVENLABS_API_KEY` | TTS narration |
| `ELEVENLABS_VOICE_ID` | Voice profile ID from ElevenLabs |
| `PEXELS_API_KEY` | Stock footage |
| `PIXABAY_API_KEY` | Stock footage fallback |
| `YOUTUBE_CLIENT_ID` | YouTube OAuth 2.0 client ID |
| `YOUTUBE_CLIENT_SECRET` | YouTube OAuth 2.0 secret |
| `YOUTUBE_REFRESH_TOKEN` | YouTube refresh token |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `MEDIA_DIR` | Local path for rendered video storage |
| `OPPORTUNITY_THRESHOLD` | Min score to generate content (default: 70) |
| `MAX_UPLOADS_PER_DAY` | Daily upload cap per channel (default: 5) |

### YouTube OAuth Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the **YouTube Data API v3** and **YouTube Analytics API**
3. Create OAuth 2.0 credentials (Desktop app type)
4. Run the auth helper to generate your refresh token:
   ```bash
   docker compose exec backend python -m app.cli auth-youtube
   ```
5. Paste the resulting `YOUTUBE_REFRESH_TOKEN` into `.env`

---

## Project Structure

```
avcos/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   │   └── v1/
│   │   ├── workers/          # Celery task modules
│   │   │   ├── trend_worker.py
│   │   │   ├── script_worker.py
│   │   │   ├── voice_worker.py
│   │   │   ├── visual_worker.py
│   │   │   ├── compose_worker.py
│   │   │   ├── publish_worker.py
│   │   │   └── analytics_worker.py
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # External API clients
│   │   │   ├── anthropic_client.py
│   │   │   ├── elevenlabs_client.py
│   │   │   ├── pexels_client.py
│   │   │   └── youtube_client.py
│   │   ├── core/             # Config, database, Celery app
│   │   └── cli.py            # Management commands
│   ├── alembic/              # Database migrations
│   ├── tests/
│   └── requirements.txt
├── frontend/                 # Next.js dashboard
│   ├── app/
│   ├── components/
│   └── package.json
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── architecture.md       # System design detail
│   ├── api-clients.md        # External API integration notes
│   └── mvp-pipeline.md       # Step-by-step pipeline walkthrough
├── CLAUDE.md                 # Claude Code memory file
└── README.md
```

---

## Dashboard

The Next.js dashboard at `localhost:3000` provides:

- **Pipeline Monitor** — live worker status and queue depth
- **Video Queue** — all videos with status (`pending → rendering → uploading → live`)
- **Analytics** — per-video views, average view duration, CTR, performance score

---

## Development

**Run tests:**
```bash
docker compose exec backend pytest tests/ -v
```

**Lint and format:**
```bash
docker compose exec backend ruff check .
docker compose exec backend black .
```

**Create a new migration:**
```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
docker compose exec backend alembic upgrade head
```

**Watch Celery logs:**
```bash
docker compose logs -f celery-render
docker compose logs -f celery-script
```

**Rebuild after code changes:**
```bash
docker compose up -d --build backend
```

---

## Opportunity Scoring

Trends are scored before content generation. Only scores ≥ 70 proceed:

```
Score = 0.40 × Virality
      + 0.25 × Engagement
      + 0.20 × Monetization
      − 0.15 × Saturation
```

Adjust the threshold via `OPPORTUNITY_THRESHOLD` in `.env`.

---

## Video Output Format

All videos render to:

- **Resolution:** 1080×1920 (vertical 9:16)
- **Codec:** H.264 video, AAC audio
- **Frame rate:** 30fps
- **Captions:** Word-level, bold white + black outline, lower-third position
- **Music:** Background track mixed at −20dB under narration
- **Duration:** ~60 seconds

---

## Roadmap

**MVP (current)**
- [x] Docker Compose stack
- [ ] Trend scraper (Google Trends + Reddit)
- [ ] Opportunity scoring filter
- [ ] Claude script generation
- [ ] ElevenLabs TTS + word timestamps
- [ ] Pexels/Pixabay footage fetch
- [ ] FFmpeg composition + captions
- [ ] YouTube Shorts upload + scheduling
- [ ] YouTube Analytics pull
- [ ] Next.js dashboard

**V2**
- [ ] TikTok + Instagram Reels publishing
- [ ] Automated learning loop (performance → prompt adjustment)
- [ ] Retention optimization engine
- [ ] Multi-platform smart scheduling

**V3**
- [ ] AI-generated video (Runway / Pika / Luma)
- [ ] Multi-agent LangGraph orchestration
- [ ] Autonomous brand personas per channel
- [ ] Kubernetes horizontal scaling

---

## Contributing

1. Branch from `main`: `git checkout -b feature/your-feature`
2. Follow conventions in `CLAUDE.md`
3. Write tests for new workers and service clients
4. Run lint + tests before opening a PR
5. PRs require a passing CI run and one reviewer approval

---

## License

MIT