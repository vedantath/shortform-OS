# Database Diagram

## Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────┐
│                    trend_signals                    │
├─────────────────────────────────────────────────────┤
│ PK  id                UUID                         │
│     source            VARCHAR(64)   NOT NULL        │
│     niche             VARCHAR(128)  NOT NULL        │
│     topic             TEXT          NOT NULL        │
│     virality_score    FLOAT         default 0.0     │
│     engagement_score  FLOAT         default 0.0     │
│     monetization_score FLOAT        default 0.0     │
│     saturation_score  FLOAT         default 0.0     │
│     opportunity_score FLOAT         default 0.0     │
│     velocity          FLOAT         default 0.0     │
│     raw_data          TEXT          nullable        │
│     created_at        TIMESTAMPTZ   server_default  │
└─────────────────────────────────────────────────────┘
          │ 1
          │ SET NULL on delete
          │ N
┌─────────────────────────────────────────────────────┐    ┌──────────────────────────────────────────────────┐
│                      videos                         │    │                   channels                       │
├─────────────────────────────────────────────────────┤    ├──────────────────────────────────────────────────┤
│ PK  id                UUID                         │    │ PK  id                  UUID                     │
│ FK  trend_signal_id   UUID → trend_signals.id      │    │     youtube_channel_id  VARCHAR(64)  UNIQUE       │
│ FK  channel_id        UUID → channels.id           │◄───│     name                VARCHAR(256) NOT NULL     │
│     status            ENUM          NOT NULL        │    │     timezone             VARCHAR(64)  default UTC  │
│                         pending                     │    │     posting_schedule     TEXT         nullable     │
│                         scripting                   │    │     daily_upload_limit   INT          default 5    │
│                         voicing                     │    │     active               BOOLEAN      default true │
│                         fetching_visuals            │    │     created_at           TIMESTAMPTZ               │
│                         rendering                   │    │     updated_at           TIMESTAMPTZ               │
│                         uploading                   │    └──────────────────────────────────────────────────┘
│                         live                        │
│                         failed                      │
│     title             VARCHAR(256) nullable         │
│     description       TEXT         nullable         │
│     tags              TEXT         nullable         │
│     youtube_video_id  VARCHAR(32)  nullable         │
│     local_path        TEXT         nullable         │
│     error_message     TEXT         nullable         │
│     created_at        TIMESTAMPTZ                   │
│     updated_at        TIMESTAMPTZ                   │
└─────────────────────────────────────────────────────┘
          │ 1
          │ CASCADE on delete
          ├──────────────────────────────────┐
          │ N                                │ N
┌─────────────────────────────┐   ┌─────────────────────────────────────┐
│           scripts           │   │              analytics              │
├─────────────────────────────┤   ├─────────────────────────────────────┤
│ PK  id           UUID       │   │ PK  id                   UUID       │
│ FK  video_id     UUID       │   │ FK  video_id             UUID       │
│                  → videos.id│   │                          → videos.id│
│ FK  prompt_      UUID       │   │     views                BIGINT      │
│     template_id  → prompt_  │   │     likes                INT         │
│                  templates.id│  │     comments             INT         │
│     version      INT        │   │     shares               INT         │
│     content_json TEXT       │   │     avg_watch_duration_sec FLOAT     │
│     model_used   TEXT       │   │     retention_rate       FLOAT       │
│     created_at   TIMESTAMPTZ│   │     ctr                  FLOAT       │
└─────────────────────────────┘   │     collected_at         TIMESTAMPTZ │
          │ N                     └─────────────────────────────────────┘
          │ SET NULL on delete
          │ 1
┌──────────────────────────────────┐
│          prompt_templates        │
├──────────────────────────────────┤
│ PK  id                   UUID              │
│     name                 VARCHAR(128) NOT NULL  │
│     version              INT         NOT NULL   │
│     purpose              VARCHAR(64)  NOT NULL  │
│     system_prompt        TEXT        NOT NULL   │
│     user_prompt_template TEXT        NOT NULL   │
│     active               BOOLEAN     default true │
│     created_at           TIMESTAMPTZ            │
└──────────────────────────────────┘
```

## Relationships

| Relationship | Cardinality | On Delete |
|---|---|---|
| `trend_signals` → `videos` | 1:N | SET NULL |
| `channels` → `videos` | 1:N | SET NULL |
| `videos` → `scripts` | 1:N | CASCADE |
| `videos` → `analytics` | 1:N | CASCADE |
| `prompt_templates` → `scripts` | 1:N | SET NULL |

## Design Notes

- All primary keys are UUIDs (`uuid4`)
- All timestamps are `TIMESTAMPTZ` (UTC-aware)
- `scripts` and `analytics` are hard-deleted with their parent video (CASCADE)
- `trend_signal_id` and `channel_id` on `videos` survive parent deletion (SET NULL)
- `scripts` is versioned — a video can have multiple script iterations linked to different `prompt_templates`
