![][image1]**T E C H N I C A L S P E C I F I C A T I O N V 1 . 0 AV![][image2]COS**   
Autonomous Viral Content Operating System — A fully autonomous AI-powered platform for short-form video discovery, generation, publishing, and self-optimization. 

**D O C UM E N T T Y P E**   
**S T A T U S**   
**V E R S I O N**   
**D A TE** 

Project Spec & Architecture   
MVP Definition   
1.0.0   
2025 

![][image3]AI Content Generation ![][image4]Short-Form Video ![][image5]Autonomous Systems ![][image6]Multi-Agent AI ![][image7]TikTok · YouTube Shorts · Instagram Reels Python · FastAPI · Next.js Redis · PostgreSQL · FFmpeg  
**N A V I G A T I O N** 

**Table of Contents** 

**O V E R V I E W** 

**01** Executive Summary & Vision 

**02** Core Concept & Value Proposition 

**03** Primary Objectives 

**M V P S P E C I F I C A T I O N** 

**04** MVP Scope & Rationale 

**05** MVP Pipeline — Step by Step 

**06** MVP Technical Architecture 

**F U L L S Y S T E M A R C H I T E C T U R E** 

**07** Core Modules — Complete System 

A. Trend Discovery · B. Opportunity Scoring · C. Content Generation · D. Voice Synthesis 

E. Visual Generation · F. Video Composition · G. Retention Optimization · H. Publishing · I. Analytics · J. Learning **08** Multi-Agent AI System 

**09** Database Architecture 

**10** Queue & Orchestration 

**11** Dashboard & Frontend 

**12** Compliance & Safety Layer 

**P L A N N I N G & D E L I V E R Y** 

**13** Technical Stack Summary 

**14** Engineering Challenges & Risk Register 

**15** Roadmap & Future Expansion  
**S E C T I O N 0 1** 

**Executive Summary & Vision** 

AVCOS is an end-to-end autonomous content engine — designed to run faceless social media brands at scale with minimal human oversight. 

**100%** 

AUTOMATED PIPELINE 

**3** 

TARGET PLATFORMS 

**10** 

CORE MODULES 

**6** 

AI AGENTS 

**What is AVCOS?** 

AVCOS (Autonomous Viral Content Operating System) is an AI-powered media platform that autonomously discovers viral trends, generates complete short-form video content, publishes across social platforms, and continuously improves output quality through closed-loop performance learning — all without human editing intervention. 

The platform operates like an **AI media company**: it monitors the internet for emerging trends, scores their monetization potential, scripts and voices video narration, assembles footage, renders finished videos, schedules uploads at peak engagement windows, and feeds performance data back into its generation models to produce better content over time. 

**The Problem** 

**Manual Content Creation is Slow** 

Human creators spend 4–12 hours per video on scripting, recording, editing, and optimization. Scaling to hundreds of channels is impossible manually. 

**Trend Windows Close Fast** 

Viral trends peak within 24–72 hours. By the time a creator identifies and acts on a trend, it has often saturated. Speed is critical. 

**Analytics are Reactive, Not Predictive** 

Creators analyze past performance but rarely build systematic feedback loops that alter future content strategy in real time. 

**Platform Diversity Requires Redundant Work** 

TikTok, YouTube Shorts, and Instagram Reels each require slightly different formats, captions, and hashtag strategies — multiplying workload. 

**The Solution**

**CORE VALUE PROPOSITION** 

AVCOS compresses the entire content lifecycle — from trend detection to published video — into a fully automated pipeline that runs 24/7, improves continuously, and scales horizontally across as many channels and niches as compute budget allows. The system's real moat is not video generation but the **self-optimization feedback loop** that makes every future video better than the last.  
**S E C T I O N 0 2** 

**Core Concept & Value Proposition** From a linear, human-driven workflow to a fully autonomous optimization loop. 

**From Linear to Autonomous** 

Traditional content creation is a linear chain that ends when a video is uploaded. AVCOS transforms this into a continuous loop where every upload generates data that improves future content. 

**⚠ Traditional Workflow** 

**Idea (Manual)** 

↓ 

**Script (Manual)** 

↓ 

**Edit (Manual)** 

↓ 

**Upload (Manual)** 

↓ 

**Analyze (Manual)** 

✕ Ends here. No feedback loop. Starts over from zero. 

**✓ AVCOS Autonomous Loop** 

**Trend Discovery** 

↓ 

**Opportunity Scoring** 

↓ 

**AI Content Generation** 

↓ 

**Media Synthesis & Edit** 

↓ 

**Publish & Collect Analytics** 

↓ 

**Learning & Optimization ↺** 

**Philosophy: The Real Moat** 

**Not: Video Generation** 

AI video tools are commoditizing rapidly. The generation layer is replaceable. 

**Not: Auto-Publishing** 

Scheduling tools already exist. Automation alone doesn't create a competitive edge.  
**Yes: Self-Optimization Loop** 

The compounding feedback cycle — where performance data reshapes every future video — is the true defensible asset. 

Every video AVCOS publishes is an experiment. Every data point returned by the platform — watch time, click-through rate, comment velocity — is a training signal. Over weeks and months, the system builds a proprietary performance model specific to each niche and audience that no competitor can replicate without running the same loop.  
**S E C T I O N 0 3** 

**Primary Objectives** 

The functional and technical goals that define success for AVCOS. 

**\# Objective Description Priority** 

1 **Content** 

**Automation** 

2 **Trend-Reactive Speed** 

3 **Cross-Platform Publishing**   
Generate complete short-form videos (script → voice → visuals → edit) without any manual intervention. 

Detect trending topics and have published content live within 30–90 minutes of trend detection. 

Distribute automatically to TikTok, YouTube Shorts, and Instagram Reels with platform-specific optimization.   
**Critical Critical Critical** 

4 **Self-Optimization** Use performance analytics to automatically refine scripts, hooks, visual styles, and   
**High** 

pacing over time. 

5 **Horizontal** 

**Scalability** 

6 **Monetization** 

**Readiness** 

7 **Compliance &** 

**Safety** 

**Success Metrics MVP Success Criteria**   
Support hundreds of concurrent content channels across multiple niches with independent optimization per channel. 

Content must meet YouTube/TikTok monetization criteria: original, brand-safe, high retention format. 

Avoid platform ToS violations through duplicate detection, copyright filtering, and content moderation.   
**High** 

**Medium Medium** 

At least 1 fully automated video per day published to YouTube Shorts End-to-end pipeline runs without human editing 

Videos meet minimum 40% average view duration 

System detects and acts on a trending topic within 2 hours 

**Full System Success Criteria** 

10+ videos per day across 3 platforms 

Performance improves measurably after 30-day learning cycle Zero manual editing required 

Channel reaches monetization threshold within 90 days  
**S E C T I O N 0 4** 

**MVP Scope & Rationale** 

The MVP deliberately constrains scope to a single platform and simplified pipeline — prioritizing a working, monetizable prototype over a complete system. 

⚠**Build Rule \#1: Do NOT build the full autonomous system first.**   
Attempting to ship all 10 modules simultaneously leads to months of development before any validation occurs. The MVP validates the core loop on a single platform with the simplest effective implementation of each step. 

**What the MVP Includes** 

**Component MVP Implementation Deferred For Later Platform** YouTube Shorts only TikTok, Instagram Reels **Trend Detection** Google Trends API \+ RSS feeds \+ Reddit scraper TikTok/Twitter real-time scraping 

**Script** 

**Generation**   
Claude or GPT-4 with structured prompt templates Multi-agent refinement loops 

**Voice (TTS)** ElevenLabs API — single voice profile Multi-voice, emotion modulation **Visuals** Curated stock footage library (Pexels/Pixabay APIs) AI-generated video (Runway/Pika/Luma) 

**Editing** FFmpeg — sequential scene assembly with auto captions   
Visual effects, motion graphics, retention optimization 

**Publishing** YouTube Data API v3 (official) Browser automation for TikTok/Instagram **Analytics** YouTube Analytics API — manual review Automated learning loop, prompt adjustment **Dashboard** Basic status dashboard (queue \+ upload log) Full analytics, prompt control, multi-account 

**Why These Choices?** 

**✓ YouTube First** 

Official API means no anti-bot risk. YouTube monetization threshold is achievable. Shorts has strong algorithmic distribution for new channels. 

**✓ Stock Footage Over AI Video** 

AI video generation costs $0.50–$5 per clip and adds latency. Stock footage from Pexels/Pixabay is free, instant, and sufficient to validate the pipeline. 

**✓ Single Voice Profile** 

One consistent voice builds channel identity faster. Multi-voice adds complexity with no immediate engagement benefit at MVP stage.  
**S E C T I O N 0 5** 

**MVP Pipeline — Step by Step** 

A detailed walkthrough of every stage in the MVP workflow, from trend detection to uploaded video. 

**STEP 1 — TREND DETECTION** 

**Trend Scraper Module** 

A scheduled Python script (runs every 30–60 min via Celery Beat) queries Google Trends, the Reddit API (r/trending, niche subreddits), and RSS feeds from YouTube's trending page. Raw signals are normalized into a common schema and written to PostgreSQL. 

`# Output schema — trend_signals table`   
`{`   
`"trend_id": "TX_2941",`   
`"niche": "space exploration",`   
`"hook_pattern": "You won't believe...",`   
`"velocity_score": 0.87,`   
`"trend_score": 82,`   
`"source": "google_trends"`   
`}` 

**STEP 2 — OPPORTUNITY FILTERING** 

**Simple Scoring Filter** 

MVP uses a lightweight scoring formula to filter out saturated or low-potential trends. Only trends scoring above a configurable threshold (default: 70\) proceed to content generation. No full ML model at this stage — rule-based with adjustable weights. 

`OpportunityScore = 0.4(Virality) + 0.25(Engagement) + 0.2(Monetization) - 0.15(Saturation)` 

**STEP 3 — SCRIPT GENERATION** 

**LLM Script Writer** 

Qualifying trends are passed to the LLM (Claude Sonnet or GPT-4) with a structured prompt template that enforces the proven 60-second script structure. The prompt includes niche context, target audience, hook type, and emotional trigger. Output is a JSON object containing narration segments with timestamps. 

`# Script structure enforced by prompt`   
`{`   
`"segments": [`   
`{ "time": "0-2s", "type": "hook", "text": "NASA just discovered..." },`   
`{ "time": "2-10s", "type": "escalation", "text": "...and it changes everything" },`   
`{ "time": "10-25s","type": "payoff", "text": "Here's what they found..." },`   
`{ "time": "25-40s","type": "twist", "text": "But wait — there's more" },`   
`{ "time": "40-60s","type": "cta", "text": "Follow for daily space facts" }`   
`]`   
`}` 

**STEP 4 — VOICE SYNTHESIS** 

**TTS Narration via ElevenLabs** 

The assembled script narration is sent to ElevenLabs API. The MVP uses a single pre-selected voice profile (e.g., calm-male-authoritative or energetic-female). The API returns a WAV/MP3 file with word-level timestamp metadata used for caption synchronization in Step 6\. 

**STEP 5 — VISUAL ASSEMBLY** 

**Stock Footage Retrieval** 

Keywords extracted from each script segment are used to query the Pexels and Pixabay APIs. The most relevant clips are downloaded and cached. A simple semantic relevance score ranks clips against the script text using a lightweight embedding model (e.g., sentence transformers). Duration of each clip is matched to the segment's time window. 

**STEP 6 — VIDEO COMPOSITION** 

**FFmpeg Assembly Engine** 

FFmpeg assembles: (1) video clips trimmed to segment durations, (2) voice audio track synchronized to timeline, (3) word-level animated captions burned into frame (bold white text \+ black outline, centered lower-third), (4) background music at \-20dB mixed under narration, (5) output encoded as 1080x1920 MP4 (9:16 vertical, H.264, 30fps) ready for YouTube Shorts. 

`# FFmpeg render pipeline (simplified)`   
`ffmpeg \`  
`-i footage_concat.mp4 \`   
`-i narration.mp3 \`   
`-i background_music.mp3 \`   
`-filter_complex "[2:a]volume=0.15[bg];[1:a][bg]amix[audio];`   
`subtitles=captions.ass[v]" \`   
`-map "[v]" -map "[audio]" \`   
`-vcodec libx264 -acodec aac \`   
`-s 1080x1920 -r 30 \`   
`output_final.mp4` 

**STEP 7 — PUBLISHING** 

**YouTube Data API v3 Upload** 

The rendered MP4 is uploaded via the official YouTube Data API v3. Title, description, tags, and category are auto-generated by the LLM alongside the script. Scheduling uses pre-defined optimal posting windows (Tue–Thu, 7–9 AM and 6–8 PM local audience time) stored as configurable channel settings. 

**STEP 8 — ANALYTICS COLLECTION** 

**YouTube Analytics API Pull** 

24–48 hours post-upload, the system queries YouTube Analytics API for: views, average view duration, click-through rate, impressions, likes, and comments. Data is stored against the video record in PostgreSQL. At MVP stage, a human reviews this data to inform prompt adjustments — the automated learning loop is deferred to V2.

 **MVP Target Throughput**   
With all APIs in place, the MVP pipeline should produce one complete video in approximately 8–15 minutes end-to-end. At this speed, the system can realistically publish 3–5 videos per day on a single machine with no GPU required.   
**S E C T I O N 0 6** 

**MVP Technical Architecture** The minimal but production-ready infrastructure required to run the MVP pipeline reliably. 

**Service Map** 

**Layer Technology Role Justification** 

**API** 

**Backend**   
**FastAPI** 

**Python 3.11**   
Orchestration, webhooks, dashboard API   
Async-native, fast to develop, ideal for task coordination 

**Task Queue Celery Redis** Async video generation jobs, scheduled scrapers 

**Database PostgreSQL** Trends, scripts, videos, analytics, schedules   
Video generation is slow; must be non blocking 

Relational model fits structured analytics data 

**LLM Claude API OpenAI**   
Script generation, caption/title writing Dual provider reduces single-point-of-failure risk 

**TTS ElevenLabs API** Narration audio generation with timestamps   
Best-in-class naturalness; word timestamps enable captions 

**Visuals Pexels API Pixabay API**   
Stock footage retrieval Free tier, high volume, no copyright risk 

**Video Render**   
**FFmpeg** Composition, captions, audio mix, encoding   
Industry standard; zero licensing cost; CPU only for MVP 

**Publishing YouTube Data API v3**   
Upload, scheduling, metadata Official API \= no ToS risk; stable, well documented 

**Storage Local / S3** Intermediate files, rendered videos Local for MVP; S3 when scaling to multiple workers 

**Frontend Next.js Tailwind**   
Status dashboard, queue monitor Minimal UI; shows pipeline state and upload history 

**Deployment Docker Compose** Local/single-server orchestration Kubernetes is deferred until multi-server scaling is needed 

**MVP Data Flow** 

`┌───────────────────────────────────────────────────────────────────────┐`   
`│ AVCOS MVP — DATA FLOW │`   
`└───────────────────────────────────────────────────────────────────────┘` 

`Celery Beat (scheduler)`   
`│ every 30 min`   
▼   
`TrendScraper Worker ──→ Google Trends API`   
`│ ──→ Reddit API`   
`│ ──→ YouTube RSS`   
`│`   
`│ writes trend_signals to PostgreSQL`   
▼   
`OpportunityFilter Worker`   
`│ score < 70? → discard`   
`│ score ≥ 70? → enqueue`   
▼   
`ScriptGen Worker ──→ Claude / OpenAI API ──→ structured JSON script`   
`│`   
`├──→ VoiceSynth Worker ──→ ElevenLabs API ──→ audio.mp3 + timestamps` 

`│`  
`└──→ VisualFetch Worker ──→ Pexels / Pixabay API ──→ footage clips │` 

▼ `(both complete)`   
`VideoCompose Worker ──→ FFmpeg`   
`│ captions (.ass) + audio mix + clip concat`   
`│ → renders output_1080x1920.mp4`   
▼   
`PublishWorker ──→ YouTube Data API v3`   
`│ uploads MP4, sets title/tags/description`   
`│ schedules for optimal time window`   
▼   
`AnalyticsWorker (T+48h) ──→ YouTube Analytics API`   
`│ pulls views / AVD / CTR / likes`   
`└──→ stores in videos.performance_score (PostgreSQL)` 

**MVP Database Schema** 

`CREATE TABLE trend_signals (`   
`id UUID PRIMARY KEY,`   
`source TEXT, -- google_trends | reddit | youtube_rss niche TEXT,` 

`topic TEXT,`   
`velocity FLOAT,`   
`score FLOAT,`   
`processed BOOLEAN DEFAULT false,`   
`created_at TIMESTAMP`   
`);` 

`CREATE TABLE videos (`   
`id UUID PRIMARY KEY,`   
`trend_id UUID REFERENCES trend_signals(id),`   
`title TEXT,`   
`script_json JSONB,`   
`audio_url TEXT,`   
`render_path TEXT,`   
`youtube_id TEXT,`   
`status TEXT, -- pending|rendering|uploaded|failed scheduled_at TIMESTAMP,` 

`published_at TIMESTAMP,`   
`views INT,`   
`avg_view_pct FLOAT,`   
`ctr FLOAT,`   
`performance_score FLOAT,`   
`created_at TIMESTAMP` 

`);`  
**S E C T I O N 0 7** 

**Core Modules — Full System** 

Detailed specification of all 10 modules in the complete AVCOS system. Modules marked **MVP** are included in the initial build; **V2+** are deferred. 

**ATrend Discovery Engine MVP**   
Continuously monitors internet platforms for emerging viral trends 

**DATA SOURCES** 

Google Trends API (keyword velocity) 

Reddit API (comment/upvote velocity by subreddit) 

YouTube Trending RSS feed 

Twitter/X Trending API **V2** 

TikTok Creative Center scraper **V2** 

**SIGNALS EXTRACTED** 

Hook patterns (POV:, "You won't believe...") 

Engagement velocity (comments/hour) 

Hashtag emergence rate 

Audio/sound trend correlation 

Niche classification via NLP 

**BOpportunity Scoring Engine MVP**   
Filters and ranks trends by content generation value 

Applies the weighted scoring formula to all incoming trends. Trends below threshold are discarded; high scorers are queued for content generation with priority ordering. At V2+, this engine incorporates historical performance data to learn which trend types perform best for a given channel. 

`Score = 0.40 × Virality + 0.25 × Engagement + 0.20 × Monetization − 0.15 × Saturation` 

**CContent Generation Engine MVP**   
Generates complete script with hooks, narration, scene breakdowns, and CTA 

**SCRIPT ARCHITECTURE (60S)** 

**0–2s:** Hook — immediate pattern interrupt 

**2–10s:** Escalation — raise stakes, build tension 

**10–25s:** Payoff — deliver on the hook promise 

**25–40s:** Twist — unexpected detail to re-engage 

**40–60s:** CTA — follow, like, comment prompt 

**PROMPT VARIABLES** 

Niche & topic from trend signal 

Target audience profile 

Historical top-performer examples 

Platform (Shorts vs TikTok vs Reels) 

Brand voice/persona instructions  
**DVoice Synthesis Engine MVP**   
Converts script narration to natural-sounding speech with timestamps 

ElevenLabs API generates MP3 audio with word-level alignment data. Word timestamps power precise caption synchronization. MVP uses one voice profile; V2 adds multi-voice profiles, emotional modulation (intensity, dramatic pauses), and dynamic pacing adjustment based on script segment type. 

**EVisual Generation Engine V2 (AI Video) / MVP (Stock)**   
Provides scene-matched visual content for each script segment 

**MVP:** Pexels/Pixabay APIs with semantic keyword matching per script segment. **V2:** AI-generated video clips via Runway, Pika, or Luma for unique, unrepeatable visuals. A fallback hierarchy ensures the system always has valid footage: (1) AI video → (2) curated stock → (3) generic B-roll. 

**FVideo Composition Engine MVP**   
Assembles all media into a final 9:16 short-form video 

**MVP OUTPUTS** 

1080×1920 H.264 MP4 

Word-by-word animated captions 

Background music at \-20dB 

Clip transitions (crossfade) 

**V2 ENHANCEMENTS** 

Zoom cuts & motion blur 

Dynamic subtitle styles 

SFX triggered by script events 

Retention-optimized cut pacing 

**GRetention Optimization Engine V2**   
Maximizes average view duration through AI-driven pacing analysis 

Uses attention modeling to predict drop-off probability at each second of the video. Dynamically adjusts cut frequency, subtitle timing, and audio pacing to minimize predicted drop-offs. Requires performance data from at least 50 published videos to train effectively. 

**HPublishing Engine MVP (YouTube)**   
Distributes content to social platforms with optimized metadata 

YouTube Data API v3 handles upload, title, description, tags, category, and scheduling. Smart scheduling selects from pre configured optimal posting windows per channel audience timezone. V2 adds TikTok (browser automation via Playwright) and Instagram Reels (API hybrid). 

**I–JAnalytics \+ Learning Engine MVP (Manual) / V2 (Auto)**   
Collects performance data and feeds it back into generation quality 

**MVP:** Pulls YouTube Analytics data into PostgreSQL for manual human review. **V2:** Automated learning loop extracts performance patterns (hook styles, script length, cut pacing, visual type) and automatically adjusts LLM prompt templates and scoring weights. Estimated improvement: 2–4× engagement increase within the first 30-day learning cycle.  
**S E C T I O N 0 8** 

**Multi-Agent AI System** 

The full AVCOS system orchestrates six specialized AI agents, each owning a discrete part of the content pipeline. MVP collapses these into a single-chain workflow; V2 enables true parallel, collaborative multi-agent operation. 

 **Trend Analyst Agent**   
Finds viral opportunities 

Continuously monitors data sources, scores incoming trends, and surfaces the highest-opportunity topics to the Creative Director. Owns the Trend Discovery and Opportunity Scoring modules. 

 **Creative Director Agent**   
Determines content strategy 

Takes the qualified trend and decides: video format, visual style, emotional tone, pacing approach, and brand voice alignment. Issues a creative brief to the Scriptwriter Agent. 

**✏Scriptwriter Agent**   
Writes complete scripts 

Receives the creative brief and generates a structured 60-second script with timed segments, hook variations, and alternative CTA options. Returns a scored JSON script object. 

 **Video Editor Agent**   
Constructs edit timeline 

Converts the script into an edit decision list (EDL): selects footage, assigns timestamps, determines cut points, and generates the FFmpeg render command. Collaborates with Visual Gen. 

 **Optimization Agent**   
Tunes for engagement 

Reviews the finished video against retention heatmap predictions. May trigger re-cuts or subtitle timing adjustments before publishing approval. At V2+, runs automatically. 

 **Publisher Agent**   
Schedules and uploads 

Handles all platform API interactions: selects optimal posting time, generates platform-specific captions and hashtags, uploads the video, and confirms successful publication. 

ℹ**MVP Agent Architecture**   
At MVP stage, these "agents" are implemented as separate Celery workers with single LLM calls per step — not a true autonomous multi-agent framework. V2 introduces orchestration via LangGraph or a custom agent loop, enabling agents to collaborate, critique each other's outputs, and iterate before a video is approved for render.  
**S E C T I O N S 0 9 – 1 2** 

**Infrastructure: Database, Queue, Dashboard & Compliance** 

**09 — Database Architecture** 

PostgreSQL is the system of record for all structured data. Redis serves dual purpose as the Celery message broker and a hot cache for trend scores and render status. 

**Table Key Columns Purpose** 

**trend\_signals** id, source, niche, topic, score, velocity Raw trend data from all scrapers **videos** id, trend\_id, status, youtube\_id, performance\_score Video lifecycle tracking **scripts** id, video\_id, segments\_json, prompt\_version Script storage \+ versioning **analytics** video\_id, views, avg\_view\_pct, ctr, likes, date Performance metrics from platforms **channels** id, platform, niche, posting\_windows, voice\_id Per-channel configuration **prompt\_templates** id, type, version, content, performance\_avg Versioned LLM prompts 

**10 — Queue & Orchestration** 

Video generation is CPU/API-bound and cannot run synchronously in an HTTP request cycle. Celery with Redis broker provides a robust, observable task queue. 

**WORKER TYPES** 

**trend-worker** — scraping & scoring (x2 instances) 

**script-worker** — LLM calls (x2 instances) 

**render-worker** — FFmpeg composition (x1–4, CPU-intensive) 

**upload-worker** — platform API calls (x2 instances) 

**analytics-worker** — scheduled data pulls (x1 instance) 

**QUEUE CONFIGURATION** 

Separate priority queues per worker type 

Retry logic with exponential backoff (3 retries) 

Dead letter queue for failed jobs 

Celery Beat for cron-style scheduling 

Flower dashboard for queue monitoring (MVP) 

**11 — Dashboard & Frontend** 

A Next.js \+ Tailwind dashboard gives operators visibility into the pipeline state without needing to query the database directly. 

**Pipeline Monitor** 

Live view of Celery queue depth, worker status, and current job progress per stage. 

**Video Queue** 

List of all videos by status: pending → rendering → uploaded → live, with trend topic and scheduled publish time. **Analytics Overview**  
Per-video performance cards showing views, average view duration, CTR, and performance score trend line. V2 additions: Prompt editor, trend explorer, multi-account management, A/B test setup, learning engine controls. **12 — Compliance & Safety Layer** 

**Duplicate Detection** 

Video fingerprinting (perceptual hash) prevents re-upload of identical or near-identical content, which triggers platform spam detection. 

**Copyright Filtering** 

All stock footage sourced only from free-commercial APIs (Pexels/Pixabay). Background music from royalty-free libraries. No user-uploaded audio. 

**Content Moderation** 

LLM-generated scripts are passed through a moderation check (OpenAI Moderation API or equivalent) before entering the render queue. 

**Platform Risk Scoring** 

Upload frequency limits are enforced per channel (max 3–5 posts/day) to avoid triggering platform spam algorithms. Rate limiting baked into Publisher Agent.  
**S E C T I O N 1 3** 

**Technical Stack Summary** 

Complete technology inventory across MVP and full-system builds. 

**Layer Technology Version / Notes Phase** API Backend Python \+ FastAPI Python 3.11, FastAPI 0.100+ **MVP** Frontend Next.js \+ Tailwind CSS Next.js 14, Tailwind 3 **MVP** Task Queue Celery \+ Redis Celery 5.x, Redis 7.x **MVP** Database PostgreSQL Postgres 15+ **MVP** Video Rendering FFmpeg FFmpeg 6+, CPU-only at MVP **MVP** LLM — Script Anthropic Claude API claude-sonnet-4 recommended **MVP** LLM — Fallback OpenAI GPT-4o gpt-4o-mini for cost efficiency **MVP** TTS ElevenLabs API Turbo v2.5 for speed **MVP** Stock Footage Pexels API \+ Pixabay API Free commercial license **MVP** Publishing YouTube Data API v3 OAuth 2.0 auth **MVP** Scraping Playwright \+ BeautifulSoup Playwright 1.40+ **MVP** Containerization Docker \+ Docker Compose Docker Compose V2 **MVP** File Storage Local → AWS S3 boto3, S3-compatible **Scale** 

CDN Cloudflare For dashboard \+ asset delivery **Scale** AI Video Gen Runway / Pika / Luma AI API integration per provider **V2** Image Gen SDXL / Flux / DALL·E Provider abstraction layer **V2** TikTok Upload Playwright browser automation TikTok no official upload API **V2** Agent Orchestration LangGraph / custom loop Multi-agent coordination **V2** Orchestration (Scale) Kubernetes AWS EKS or GKE **V3** GPU Compute AWS G4/G5 instances For AI video generation at scale **V3**  
**S E C T I O N 1 4** 

**Engineering Challenges & Risk Register** Known failure modes, their severity, and recommended mitigations. 

**Risk Severity Likelihood Mitigation** 

**Platform Anti Bot Detection**   
**High Medium** Use only official APIs at MVP (YouTube). For TikTok V2, rotate accounts, use residential proxies, enforce human-like upload intervals. Never exceed 5 

uploads/day per account. 

**AI Video Generation Cost**   
**Medium Low (MVP)** 

MVP uses free stock footage, eliminating this cost entirely. V2 implements cost per-video budget caps and provider switching based on price performance. 

**LLM Output Inconsistency** 

**Copyright** 

**Infringement** 

**Virality** 

**Prediction** 

**Accuracy** 

**ElevenLabs / API Downtime** 

**YouTube** 

**Account** 

**Strikes** 

**FFmpeg** 

**Memory /** 

**Render Crash**   
**Medium Medium** Strict JSON output schema enforced by Pydantic validation. Fallback to secondary LLM provider on parse failure. Script structure is template-constrained, not 

freeform. 

**High Low** Whitelist-only media sources (Pexels, Pixabay, royalty-free music libraries). Perceptual hash duplicate detection. No user-uploaded or scraped audio. 

**Medium High** Virality is inherently unpredictable. System mitigates by producing high volume: even 10% hit rate at 5 videos/day generates consistent winners. Focus on 

process, not prediction. 

**Medium Low** Circuit breaker pattern: fall back to PlayHT for TTS. Jobs remain in queue and retry automatically. Alert triggers if queue depth exceeds 10 stuck jobs. 

**High Medium** Content moderation pre-render. Conservative posting frequency. Unique AI generated content per video (no reposts). Manual review flag for any auto 

generated content in sensitive niches. 

**Low Medium** Celery task timeout (15 min max). Auto-retry up to 3 times. Worker health check restarts crashed containers. Dead letter queue captures all failures for manual 

inspection.  
**S E C T I O N 1 5** 

**Roadmap & Future Expansion** 

A phased delivery plan from working prototype to autonomous multi-platform media company. 

**PHASE 1 — MVP (WEEKS 1–8)** 

**Validate the Core Loop on YouTube Shorts** 

Build the 8-step pipeline: trend scraper → opportunity filter → LLM script → ElevenLabs TTS → stock footage assembly → FFmpeg composition → YouTube API upload → analytics collection. Target: 1 video/day, fully automated, zero manual editing. 

**PHASE 2 — V2 (WEEKS 9–20)** 

**Multi-Platform \+ Automated Learning Loop** 

Add TikTok and Instagram Reels publishing. Implement the automated learning engine — performance data from YouTube begins automatically adjusting LLM prompt templates. Add Retention Optimization Engine with cut-pacing analysis. Target: 5 videos/day across 3 platforms, measurably improving performance. 

**PHASE 3 — V3 (WEEKS 21–36)** 

**Multi-Agent AI \+ AI Video Generation** 

Replace the linear pipeline with a true multi-agent system (LangGraph). Integrate Runway/Pika for AI-generated video clips. Introduce autonomous brand personas — distinct AI personalities per channel with consistent visual style, voice, and content strategy. 

**PHASE 4 — V4 (WEEKS 37+)** 

**Scale to Hundreds of Channels** 

Kubernetes deployment for horizontal scaling. Per-channel niche optimization. Real-time trend reactivity targeting sub-30-minute time-to publish. AI thumbnail A/B testing. Reinforcement learning for content strategy optimization. Optional: AI comment engagement system.

**Advanced Feature Backlog** 

  **Reinforcement Learning Engine** 

Dynamic optimization of generation parameters using video performance as the reward signal. Requires 200+ video history per niche to be statistically meaningful. 

  **AI Thumbnail A/B Testing** 

Generate 3–5 thumbnail variants per video, run controlled splits, and automatically select the highest-CTR design for the permanent thumbnail. 

**⚡ Real-Time Trend Reactivity** 

WebSocket-based trend monitoring pipeline that can have a video rendered and scheduled within 15–30 minutes of a trend breaking — before saturation occurs. 

  **Autonomous Brand Personas** 

Distinct AI personalities per channel: consistent voice profile, visual style guide, content calendar cadence, and audience persona that evolves based on comment sentiment analysis. 

**FINAL PRINCIPLE** 

AVCOS is not an AI video generator — it is an **autonomous short-form media operating system**. The videos are the product. The optimization loop is the business. Every video published is data. Every data point compounds the system's advantage. The longer it runs, the harder it becomes to replicate — because the real asset is the proprietary performance model that only exists inside a system that has been running, learning, and improving for months. 

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAqwAAAAaCAYAAAByzg5xAAAEd0lEQVR4Xu3dwW8UZRzG8SFGKWo8eTAmeGmXmzctq852i5JgVKLGcAETA6jQ7ewSNFoStcTyL3qV1gR3tzH+D/7e2SmlTxfhedsuTfgePulsu++3PT6ZTLpFVY6Lfmf7ceb6nfGFfme00lgLP4ef/s8AAAAAzzXdh4+4E26Hbxqt2Ju7+7PcLqr42lveqrUX7hXFlMF6IlycGKfol6HrGAAAAOC5pvtwivONb6tydCs26VsJgxUAAAAzoftwigMN1ssxVK9M7AsDAAAAhyoG6/nYpD8m8fp01RnvDtbWxr7BeimG6lcaAQAAAI7WeHlidCsG65vTBmu7cT3eOCUAAAAAHKW0Qesder7qjNZ6y5snknZr95EABisAAACeoScP1t5EfRt2SgAAAAA4Sg8HazcG65UYq28nO4P1jfjh1Qk9CAAAAMzCnsHajbF6PWkG6+hCVQ4/TvYfBAAAAGZh72Bd6d7/IYnB+mK6w5r+M8DDNwAAAADPktxhfYXBCgAAgGOFwQoAAIBjrRmsXyft1sZrDFYAAAAcK81gvZrEYH01DdbPY6x+NLH/AAAAADBL9WDtbvaTs62NkwxWAAAAHCvTButCjNXLE/sPAAAAALPUPBJQJe3WRv3BASdirA4m9h8AAAAAZikG6xcxVstkZ7AWMVY/SapyeEkPAAAAALMUg/VOjNWTCYMVAAAAx87jButLSQzWfryJj2gFAADAs/JdVY7eibFaJO3W70XR/2A7jHfMhf6g3P600U3ie7VBeRQmv+NgtOnSnkt7Lu3l0q5Ley7tubTn0l4Obbq059KeS3su7eXQpkt7Lu25tJdLuy7tubTn0p5Lezm06dKeS3su7bm0l0ObLu25tOfSXi7turTn0p5Ley7t5dCmS3u7+rUYquU/N5JBOXqvX24Xq92t2vutu0WxWg6LqjNqpOvhy1U5HDRi4Q7Phe7E37V+Z1irAAAAAEezJx9xsVp6sFYtjcukvzQu+uW/Ra/7oNZu3SviYqvoLf/VSNd7nAm9sNZYXeluXg/XJu5fu7n05wGlxkFp06U9l/Zc2sulXZf2XNpzac+lvRzadGnPpT2X9lzay6FNl/Zc2nNpL5d2Xdpzac+lPZf2cmjTpT2X9lzac2kvhzZd2nNpz6W9XNp1ac+lPZf2XNrLoc2nlzbjzbQZG/H6+5XlzdthrfHZyrnNUyuxRSfu148C3Pjwj9rZM2sM1sP5G7Tn0l4u7bq059KeS3su7eXQpkt7Lu25tOfSXg5turTn0p5Le7m069KeS3su7bm0l0ObLu25tOfSnkt7ObTp0p5Ley7t5dKuS3su7bm059JeDm0+vUMZrIvzd4uzD60/yclwanH+t0OTegelTZf2XNpzaS+Xdl3ac2nPpT2X9nJo06U9l/Zc2nNpL4c2Xdpzac+lvVzadWnPpT2X9lzay6FNl/Zc2nNpz6W9HNp0ac+lPZf2cmnXpT2X9lzac2kvhzYtC2J+fS6aL4Rix7sLv4b12uL8L/XuXEzX4fTrF4r/AJmAR46RITsIAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHMAAAAYCAYAAADJcMJ/AAAAkUlEQVR4Xu3aQQrCQBAF0cEZNIqJkkXibefoYze0geAJ+lOLd4LaVhljFNPC3TyQhveqoXjIyWxhMTPS8F57aMTM7S/map5IbyamjoWYOogphJhCiCmEmEKIKYSYQogphJhCiCmEmEKIKYSYQogphJhCiCnguA485tV8wtu8kIb3+rWrxMztHLP37mq4IZ1LKF/Gig9zlokQXgAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF8AAAAYCAYAAACcESEhAAAArElEQVR4Xu3ZOw7CMBBFUUcQfuIXEMp6vDJLybojM0PcRNT2a25xminvlC/knIPpi7O5oBrv27lpmoKH98OnuJsbqnmY0Vn8jvht/cV/myuaGZzF74nf3tMRX4P4QsQXIr4Q8YWIL0R8IeILEV+I+ELEFyK+EPGFiC9EfCHiqyzL8nIWf+/xT7lMW3n9ik9dqGOw8KOb5/k3oBO/nW38lJLbFUdUdUhr7xBjDF9pBVmLAAgmBgAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHEAAAAYCAYAAADNhRJCAAAA2klEQVR4Xu3aTQqDMBCG4WihYtVad3ocTxYhHsyDqel8NNI/D5AM3+IhgXH34mpilmUx+75fYNu2Us6b957iVoocnHPGSDgEHEDudzkbGVLcWtGDRMwYMU1/ESvRwLqutUSsZUjx60AiXhGx/sSIycDf2ErEwpwMKQ2MqAAjKsCICjCiAoyoACMqwIgKMKICjKgAIyrAiAowogKMqAAjKvAVsfLvjfHvhxQZ7HvD7rcDh6Wwfz24GYKHD4UpThIOELCHeZ4zRkzMaURrLeRBQXGbpum4ZzCOo3kCB0BcnoTTz98AAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFEAAAAYCAYAAACC2BGSAAAAt0lEQVR4Xu3YOw7CMBBFUROEkINJKAjKbr01L8wfZogpCBIx0StfcTSWxtUtXNiEEEzOuVMpJSuzL6XQtlNljITTgLOS8yjzKgv6bRBTdWHEfb4iWjGoGKOTiE4W1G7SiL1wb4z4t7spyyO5XlA7RgRgRABGBGBEAEYEYEQARgRgRABGBGBEAEYEYEQARgRgRIBXRFuWn1q1vkDbJo3Yibm6iZE2aadHZRlxn8+I3nt1qM7U7FiZJ02ok77DP2+PAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAAAYCAYAAAC/ZrKxAAAAwUlEQVR4Xu3VW0rEQBBA0cYo6pAZBcfHbrO27CuTtjo2QhRqAzkfhyqo70uVeZ7Luq5Dc7vdnmOeaq1wZA9dKRHFfUTx2cR+iXmOAxzVJbx3J4HA3r9AxnBulmUZI5AxDkCt1xZIi6NFshEI/Hor9eet/D0AAoGUQCAhEEgIBBICgYRAICEQSAgEEgKBhEAgIRBICAQSAoGEQCCxBdKWFolQYG8LZAhf3Wt4gQNrDXx0TwKBvX0g0zQ1d90jMA1d+QbX0sAuMXcRSQAAAABJRU5ErkJggg==>