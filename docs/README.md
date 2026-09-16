# JiETNG Documentation

This directory contains the VitePress documentation site for JiETNG.

## Commands

```bash
cd docs
npm install
npm run docs:dev
npm run docs:build
npm run docs:preview
```

The production build is generated in:

```text
docs/.vitepress/dist/
```

## Current Structure

```text
docs/
├── .vitepress/
│   ├── config.mts
│   └── theme/
├── commands/
│   ├── basic.md
│   ├── index.md
│   └── record.md
├── features/
│   └── search.md
├── guide/
│   └── getting-started.md
├── more/
│   ├── faq.md
│   ├── license.md
│   ├── privacy.md
│   └── support.md
├── en/
│   └── ...
├── ja/
│   └── ...
├── public/
│   ├── bookmarklet/
│   └── ...
├── bookmarklet.md
├── demo.md
├── developer-api.md
└── index.md
```

The root locale is Japanese. Simplified Chinese pages are served under `/zh/` from the root Markdown sources, English pages live under `/en/`, and Japanese source files live under `docs/ja/`.

## Content Scope

The docs should describe the current JiETNG behavior:

- LINE Bot commands and self-only rules
- SEGA account binding and `maimai update`
- Import Token users and bookmarklet uploads
- B-series score images, filters, record lookup, plate progress, and nearby arcade search
- Developer API and user Import API

Do not edit generated files under `docs/.vitepress/dist/` or dependency files under `docs/node_modules/`.

## Deployment Notes

The VitePress config uses:

- `base: '/'`
- sitemap hostname: `https://jietng.matsuk1.com`
- local search
- locales: root `ja`, `/zh/`, `/en/`

For hosted builds, use:

```text
Build command: cd docs && npm install && npm run docs:build
Output directory: docs/.vitepress/dist
Node version: 18+
```

## Behavior audit — 2026-09-16

This pass checked all three locales against the repository implementation, not a live production deployment. Preserve the distinction when updating these pages: a successful docs build does not verify LINE delivery, SEGA login, production configuration, or external integrations.

| Pages (all locales) | Implementation checked | Corrections / verified behavior |
| --- | --- | --- |
| Home | `modules/commands/command_config.py`, `main.py` recognition handlers | Added recognition entry; preserved LINE onboarding and shared home components |
| Getting started / basic commands | `main.py` account routes and `COMMANDS`, `modules/bindtoken_manager.py`, `templates/settings.html`, `modules/images/skins.py` | Web unbind confirmation; token lifetimes; first import token; skins/backgrounds; ranking/mention switches; user revocation including owner association |
| Command index / records | `main.py:select_records`, `generate_level_rank_progress`, `generate_level_records`, recognition handlers; `modules/commands/*` | All public rank aliases and filters; AP/FDX 35+15 split; Recent limits; category progress; supported levels; quoted-image rec/crop/info; manual correction; friend vs mention behavior |
| Search | `modules/song_matcher.py`, `modules/commands/command_parsers.py`, `modules/api/song_api.py` | Title/alias matching (not a generic typed ID command), result caps, BPM ambiguity, Import Token data source |
| Bookmarklet | `bookmarklet/maimai-session-exporter.js`, `main.py` session-image endpoint | Generate versus Upload; localStorage token; persistent tab session cache; JPEG response and legacy filename mismatch |
| Demo | `main.py:demo_page`, locale demo scripts | Added supported sun50 option; JPEG download name; existing credential-cookie behavior documented |
| Developer API | `modules/api/{api_auth,developer_api,image_api,song_api,score_api,record_transfer_api}.py`, `modules/import_manager.py`, `modules/score_recognition/presentation.py` | Admin-managed developer tokens; button-based consent; owner/granted permissions; required create fields; PUT vs web rebind; stream failure events; PNG/base64 vs JPEG; import partition and profile replacement |
| FAQ / support | Same feature sources plus `modules/maimai_manager.py` nearby stores | Current onboarding, privacy switches, OCR troubleshooting, stale bookmarklet data, expired links, demo CORS; removed unsupported donate command |
| Privacy | `main.py` credentials/settings/demo/recognition; `modules/user_{manager,db}.py`, import token storage; demo/bookmarklet browser storage | Removed unsupported password-encryption claim; documented visibility, cookies, uploads, and limits of unbinding cleanup |
| License | Root `LICENSE` | License terms remain unchanged; this pass does not grant new usage rights |

### Implementation follow-ups (not silently changed by this docs pass)

- SEGA passwords are written directly into user JSON by the current application. Field-level encryption is not implemented; documentation must not promise it. Infrastructure-level encryption cannot be determined from these files.
- Demo “remember credentials” stores the password in a browser cookie for 90 days. This behavior was documented, not redesigned.
- Bookmarklet records persist in sessionStorage without a freshness check. Its download helper still defaults to a `.png` name although session-image now returns JPEG. Documented the workaround; source bookmarklet behavior remains unchanged.
- `r50` does not honor page/count multipliers or DX sorting. `levels`/`prog` reject decimal constants, and their `14+` group includes 15. Avoid copying B-series semantics to these commands.
- Developer API search contains a too-many-results branch, but the current matcher already caps its result list. Document the effective cap rather than promising that branch will run.

### Future updates

For a behavior change, update the root Chinese source, `en/`, and `ja/` together. Check handlers and their called helpers, not just help strings. Run `npm run docs:build` and check representative examples. Never exercise live unbind, sync, credential submission, imports, or permission mutations just to validate documentation.
