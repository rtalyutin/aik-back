# AIK Media Pipeline Overview

This document captures the end-to-end media ingestion and processing workflow that powers the AIK backend. It aggregates the high-level flow, service interactions, job lifecycle, and integration contracts that external clients must follow.

## 1. Сквозной поток (Flowchart)

```mermaid
flowchart TD
    A[SPA/Client] -->|POST /v1/uploads| B[Init multipart]
    B --> C[S3 presigned parts]
    A -->|PUT parts to S3| D[Object parts]
    A -->|POST /v1/uploads/{id}/complete| E[assetId]
    A -->|POST /v1/tracks/import {assetId, lyrics?}| F[jobId, trackId]
    subgraph Pipeline
      F --> G[Separation]
      G --> H{Lyrics provided?}
      H -- yes --> I[Align-fast]
      H -- no --> J[ASR]
      J --> I
      I --> K[QC]
      K --> L[Publish vN]
    end
    L --> M{GET /v1/tracks/{id}/ready}
    M -- 425 Not Ready --> N[/Retry with backoff/]
    M -- 200 OK --> O[minusUrl + karaoke-json]
    O --> P{Need edits?}
    P -- yes --> Q[PATCH /lyrics -> V(n+1)]
    Q --> R[POST /tracks/{id}/reprocess align]
    R --> L
    P -- no --> S[GET /assets (minus/vocals/mix)]
```

## 2. Взаимодействия (Sequence)

```mermaid
sequenceDiagram
    participant C as Client (SPA)
    participant O as Orchestrator (aik-back)
    participant S3 as S3 Storage
    participant ASR as ASR Service
    participant AL as Aligner

    C->>O: POST /v1/uploads
    O-->>C: presigned parts
    C->>S3: PUT part 1..N
    C->>O: POST /uploads/{id}/complete
    O->>S3: HEAD bucket/object
    O-->>C: {assetId}

    C->>O: POST /tracks/import {assetId, lyrics?}
    O-->>C: {jobId, trackId}
    par Separation
      O->>S3: GET object
      O->>O: run separation
    end
    alt lyrics absent
      O->>ASR: POST /transcribe
      ASR-->>O: transcript
    end
    O->>AL: POST /align {audio, lyrics}
    AL-->>O: sync map
    O->>O: QC + publish vN
    C->>O: GET /tracks/{id}/ready
    O-->>C: 200 {minusUrl, lyrics(karaoke-json)} or 425

    opt edits
      C->>O: PATCH /tracks/{id}/lyrics
      O->>O: create V(n+1)
      C->>O: POST /tracks/{id}/reprocess {"steps":["align"]}
      O->>AL: re-align
      O->>O: publish v(n+1)
    end

    C->>O: GET /tracks/{id}/assets
    O-->>C: presigned URLs (TTL short)
```

## 3. Стейт-машина Job

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> running: worker picked
    running --> succeeded: all steps ok
    running --> failed: step error
    failed --> running: retry
    running --> canceled: manual stop
```

## 4. Узлы интеграции и правила

- **Корреляция клиента:** каждый запрос клиента к API должен содержать `X-Client-Id`.
- **Пресайны:** URL для загрузки/выгрузки в S3 выдаются короткоживущими и привязаны к IP клиента.
- **Таймауты:** проверка доступности (health) для внешних зависимостей — до 1.5 секунды; каждый шаг пайплайна имеет собственные SLA.
- **Ошибки:** ответы об ошибках оформляются по RFC 7807 и включают `traceId`.
- **События наружу:** при импорте трека клиент передает `callbackUrl`; бэкенд посылает подписанные HMAC события `track.ready`, `job.failed`, `lyrics.updated`.

## 5. Дополнительные заметки

- Воронка публикации поддерживает множественные версии (vN) трека. Любые правки текста ведут к созданию новой версии и повторному шагу `align`.
- Получение ассетов доступно только после публикации и должно использовать пресайны с коротким TTL.

Эта схема служит основой для более детальной спецификации API и согласования интеграции между фронтендом и сервисами распознавания/синхронизации.
