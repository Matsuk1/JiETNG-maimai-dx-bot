# Developer API

Base URL: `https://jietng-endpoint.matsuk1.com`. Developer endpoints use `Authorization: Bearer <developer_token>`; imports use `Authorization: Bearer <import_token>`. They are not interchangeable.

## Tokens and permissions

Service administrators create and revoke developer tokens in the admin panel. Contact the maintainer for integration access. Core LINE commands no longer provide `devtoken create/list/revoke/info`. Users get an Import Token on the import-only registration success page or through `settings`; plaintext is shown once.

A developer token may access users it created (owner) or users who accepted its permission request (granted). Request access with `POST /api/v2/users/<user_id>/permissions`, optionally passing JSON `requester_name`. LINE users accept/reject through buttons in the permission message; those button actions are not plain-text chat commands.

| Method | Path | Permission / parameters |
|---|---|---|
| GET | `/api/v2/users` | Users accessible to the current token |
| POST | `/api/v2/users` | Required JSON/form `user_id`, `nickname`; returns 201 with `bind_url`, `token`, `expires_in`; existing user returns 409 |
| GET | `/api/v2/users/<user_id>` | owner or granted; user data excluding SEGA ID/password and other sensitive fields |
| DELETE | `/api/v2/users/<user_id>` | owner only; deletes user |
| GET | `/api/v2/users/<user_id>/permissions/requests` | owner only; pending requests |
| PATCH | `/api/v2/users/<user_id>/permissions/requests/<request_id>` | owner only; JSON `action`: `accept` or `reject` |
| DELETE | `/api/v2/users/<user_id>/permissions/<token_id>` | owner only; revoke granted access |
| DELETE | `/api/v2/users/<user_id>/permissions/self` | Relinquish granted access; owners cannot self-revoke |

## Binding and web links

These endpoints require owner or granted access:

```http
POST /api/v2/users/<user_id>/bind
PUT /api/v2/users/<user_id>/bind
GET /api/v2/users/<user_id>/bind-url
GET /api/v2/users/<user_id>/rebind-url
GET /api/v2/users/<user_id>/settings-url
```

POST requires `sega_id` and `password`; optional fields are `ver` (jp/intl), `aime`, `timezone`, `language`. PUT requires an existing full binding and can update `sega_id`, `password`, `ver`, `aime`, preserving language/time zone. Unlike LINE's rebind web form, API PUT can change the SEGA ID.

Bind/rebind links last 120 seconds; settings links last 1800 seconds. Link endpoints return 201. Deliver account-action links only to the corresponding user.

## Sync

```http
POST /api/v2/users/<user_id>/sync/stream
```

Requires user access and full SEGA binding. The response is `application/x-ndjson`: after obtaining the sync lock, it emits `accepted`, then `completed` or `failed`. An already-running sync can return `failed` immediately without `accepted`. HTTP 200 does not prove sync succeeded; read the final event. Authentication/rate-limit errors before streaming use HTTP error statuses. Import-only users should use the Import API.

## Images and song data

```http
GET /api/v2/users/<user_id>/image?command=b50
GET /api/v2/users/<user_id>/songs/<song_id>/image
GET /api/v2/users/<user_id>/plate?title=真神
GET /api/v2/users/<user_id>/achievement?level=14%2B&rank=sss
GET /api/v2/songs/<song_id>/image?ver=jp
GET /api/v2/users/<user_id>/export?fmt=json
GET /api/v2/songs/search?q=ヒバナ&ver=jp&max_results=10
GET /api/v2/versions
GET /api/v2/dxdata?ver=jp
```

User images/exports require access and stored data. Images default to PNG; `format=base64` returns `{ "success": true, "format": "base64", "image": "..." }`. Exports use `fmt=json` or `fmt=xml`. Omit `rank` on `achievement` for a chart list. The plate/achievement APIs do not expose LINE's `-uc/-up/-c` filters.

`songs/search` accepts `max_results` from 1–50 (default 10). The current matcher returns at most that many entries; broad queries may return only the first candidates, so refine the query. Version precedence is explicit `ver`, then an authorized `user_id`'s version, then `jp`. No matches is a successful response with empty `songs`. Use returned song IDs in song-image requests.

### Score-result OCR

```http
POST /api/v2/score-recognition
Authorization: Bearer <developer_token>
Content-Type: multipart/form-data
```

Multipart fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | file | yes | JPEG, PNG, or WebP result image; defaults to 20 MiB and 40 million pixels maximum |
| `ver` | text | no | `jp` or `intl`; defaults to `jp` and selects the song/chart dataset |

OCR runs synchronously. A response is successful only when the title, achievement, and complete judgement table can be matched and validated against one chart. Results that cannot be fully validated return `422`. Missing judgements may be inferred by Calc; inferred values are not direct readings from the image.

```bash
curl -X POST https://jietng-endpoint.matsuk1.com/api/v2/score-recognition \
  -H "Authorization: Bearer <developer_token>" \
  -F "ver=jp" \
  -F "image=@result.jpg"
```

The successful JSON contains:

- `song`: dxdata `id`, canonical `title`, and `type` (`dx` or `std`).
- `chart`: `difficulty`, displayed `level`, and numeric `internal_level`.
- `score.achievement`: recognized achievement percentage.
- `score.judgements`: fixed `tap`, `hold`, `slide`, `touch`, and `break` rows; each contains `critical_perfect`, `perfect`, `great`, `good`, and `miss`.
- `score.break_detail`: the current most likely BREAK sub-grades shown by the Flex result. `candidate_count` counts sub-grade candidates within the selected BREAK row; optional `row_candidate_count` counts feasible aggregate rows when Calc inferred the entire row. It is `{}` when no discrete match is available.
- `validation`: title match type, row/column alignment, MISS corrections, Calc range/corrections, and uncertain OCR cells.

Example response:

```json
{
  "success": true,
  "song": {"id": "50d3df", "title": "Little \"Sister\" Bitch", "type": "dx"},
  "chart": {"difficulty": "master", "level": "13+", "internal_level": 13.8},
  "score": {
    "achievement": 100.5658,
    "judgements": {
      "tap": {"critical_perfect": 403, "perfect": 225, "great": 15, "good": 0, "miss": 1},
      "hold": {"critical_perfect": 18, "perfect": 7, "great": 0, "good": 0, "miss": 0},
      "slide": {"critical_perfect": 98, "perfect": 0, "great": 0, "good": 0, "miss": 0},
      "touch": {"critical_perfect": 66, "perfect": 0, "great": 0, "good": 0, "miss": 0},
      "break": {"critical_perfect": 20, "perfect": 13, "great": 0, "good": 0, "miss": 0}
    },
    "break_detail": {"critical_perfect": 20, "perfect_high": 12, "perfect_low": 1, "great_high": 0, "great_middle": 0, "great_low": 0, "good": 0, "miss": 0, "candidate_count": 1}
  },
  "validation": {
    "title_match_type": "exact",
    "exact_title_match": true,
    "compared_rows": 5,
    "matching_rows": 5,
    "row_offset": 0,
    "column_offset": 0,
    "miss_corrections": {},
    "achievement_calc": {"observed": 100.5658, "minimum": 100.4749, "maximum": 100.5733, "consistent": true, "complete": true},
    "calc_corrections": [],
    "uncertain_cells": []
  }
}
```

### OCR result image

`POST /api/v2/score-recognition/image` accepts the same multipart `image` and `ver` fields, limits, and authentication as the JSON endpoint. A successful request returns the rendered result as `image/png`:

```bash
curl -X POST https://jietng-endpoint.matsuk1.com/api/v2/score-recognition/image \
  -H "Authorization: Bearer <developer_token>" \
  -F "ver=jp" \
  -F "image=@result.jpg" \
  --output ocr-result.png
```

When Calc finds multiple valid results, the image endpoint renders the highest-ranked candidate. `X-JiETNG-OCR-Candidate-Index` and `X-JiETNG-OCR-Candidate-Count` report its index and the total candidate count.

The server upload limit can be changed with `SCORE_RECOGNITION_API_MAX_IMAGE_BYTES`. Requests are rate-limited per developer token.

`/songs/search` chooses the version in this order: explicit `ver`, then the version stored on `user_id`, then `jp`.

`command` accepts the same B-series words users can type:

| command | Meaning |
|---------|---------|
| `b50` / `best50` | Best 50 |
| `b40` / `best40` | Best 40 |
| `b35` / `best35` | Best 35 |
| `b15` / `best15` | Best 15 |
| `ab35` / `allb35` | All Best 35 |
| `ab50` / `allb50` | All Best 50 |
| `apb50` / `ap50` | AP Best 50 |
| `fdxb50` / `fdx50` | FDX Best 50 |
| `rct50` / `r50` | Recent 50 |
| `idealb50` / `idlb50` | Ideal Best 50 |
| `s50` / `sun50` / `寸50` / `寸止め` | Near-miss 50 for SSS+ / SSS |
| `unknown` | Songs with unknown version |

Filters can be included in the command string, for example `b50 -lv 14.7`.

## Bookmarklet Image Endpoint

```http
POST /api/web/session-image
Content-Type: application/json
```

Receives bookmarklet JSON and returns `image/jpeg`. It does not require a developer token.

Core body:

```json
{
  "version": "jp",
  "cmd_type": "best50",
  "command": "-lv 14",
  "timezone": 9,
  "profile": {
    "name": "Player",
    "rating": "15000"
  },
  "records": {
    "best": [
      {
        "name": "Song Title",
        "difficulty": "master",
        "type": "dx",
        "score": "100.5000%",
        "dx_score": "1234",
        "score_icon": "sssp",
        "combo_icon": "ap",
        "sync_icon": "fdx"
      }
    ]
  }
}
```

`version` accepts only `jp` or `intl`. `cmd_type` accepts `best50`, `best40`, `best35`, `best15`, `allb35`, `allb50`, `apb50`, `fdxb50`, `idlb50`, or `sun50`; use `command` for filters such as `-lv 14`. `profile` and at least one valid item in `records.best` are required.

Image labels are fixed by server version: `jp` renders Japanese and `intl` renders English. User language preferences and other language fields in the request do not override the image language.

This endpoint generates an image only. Use Import API to save records.

## Import Records

Users create Import Tokens from the `settings` page. Plaintext is shown only once.

```http
POST /api/v2/import/records
Authorization: Bearer <import_token>
Content-Type: application/json
```

Example:

```json
{
  "version": "jp",
  "profile": {
    "name": "Player",
    "rating": 15392,
    "trophy": "真皆伝",
    "trophy_content": "真皆伝",
    "trophy_url": "https://...",
    "icon_url": "https://...",
    "nameplate_url": "https://...",
    "class_rank_url": "https://...",
    "course_rank_url": "https://..."
  },
  "records": {
    "best": [
      {
        "title": "Song Title",
        "type": "DX",
        "difficulty": "Master",
        "achievement": 100.5,
        "dx_score": 1234,
        "dx_score_max": 1500,
        "rank": "SSS+",
        "combo": "AP+",
        "sync": "FDX+"
      }
    ],
    "recent": []
  }
}
```

`rating_block_path` does not need to be uploaded; the server derives it from `rating`.

Replacement rules:

- `"records": {"best": []}` clears Best.
- `"records": {"recent": []}` clears Recent.
- Omitting a section keeps existing server data.

Success:

```json
{
  "success": true,
  "user_id": "U...",
  "best_count": 1200,
  "recent_count": 50,
  "version": "jp",
  "message": "Records imported successfully."
}
```

## CORS

The production API allows these origins:

- `https://maimaidx.jp`
- `https://maimaidx-eng.com`
- `https://dxrating.net`

Local development also allows `http://localhost:5173` and `http://127.0.0.1:5173`.

## Error Codes

| Status | Typical reason |
|--------|----------------|
| `400` | Invalid parameters or payload |
| `401` | Invalid token or SEGA credentials |
| `403` | Missing permission |
| `404` | User, token, request, or task not found |
| `409` | Binding conflict |
| `413` | OCR image exceeds the upload limit |
| `415` | Unsupported OCR image format |
| `422` | Valid image that cannot be recognized and validated as a complete score |
| `429` | Rate limit exceeded |
| `503` | Official maintenance or full sync queue |

## Safety

- Do not ship developer tokens or Import Tokens in public frontend code.
- Import Tokens are for the user's own browser or trusted tools.
- Third-party applications should use developer token plus user permission flow.
- When unlinking, call `DELETE /api/v2/users/<user_id>/permissions/self`.

## Import boundaries and clients

`records` must contain `best` or `recent`. An explicit `[]` clears that partition; omitted partitions retain old records. Sending both partitions empty returns 400. Omitted partitions return `null` for the corresponding `best_count` / `recent_count`.

Every import rebuilds the entire `profile`, including requests that omit it. Missing name, Rating, and display fields receive defaults (`Imported`, `0`, `N/A`), not previous values. Version precedence is `maimai_version`, then `version`, then stored version, then JP. Invalid versions currently fall back to JP; clients should send only `jp` or `intl`.

The repository's `client/` provides synchronous/asynchronous Python clients. `discord_bot/` is a separate Developer API integration whose slash commands differ from LINE text commands. See those directories' READMEs for integration/deployment.

`achievement` currently accepts only `11`, `11+`, `12`, `12+`, `13`, `13+`, `14`, `14+`, `15`, not LINE prog categories or decimal constants. Users can revoke the owner association through settings; this differs from an owner token being unable to self-revoke through `/permissions/self`.
