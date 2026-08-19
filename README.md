# Social OSINT

Modular OSINT scanner framework. Search a target keyword across social
platforms, analyze discovered profiles (name extraction, image hashing,
OCR, correlation), score risk signals, and explore results in a
dashboard with link analysis.

Legal use only: public information, lawful OSINT, research, defensive
security, authorized investigations. See `skills.md`.

## Quickstart

```bash
pip install -r requirements.txt
playwright install chromium

# CLI scan (interactive)
python social_osint.py

# CLI scan (arguments)
python social_osint.py --target "keyword" --platform github --platform gitlab

# Dashboard (default http://localhost:8000)
python dashboard/app.py

# Dashboard membaca folder report lain (mis. hasil scan dari folder OSIKINT)
python dashboard/app.py --output /path/ke/OSIKINT/output
```

## Dashboard

The Flask dashboard consumes JSON reports only — the core engine is not
coupled to the web layer.

- **Dashboard** `/` — totals, risk distribution, platform breakdown
- **Sessions** `/sessions` — every scan run
- **Profiles** `/profiles` — search + filter (platform, risk, keyword)
- **Profile detail** — account names, image evidence, OCR, match
  details, raw JSON
- **Link Analysis** `/link-analysis` — connection graph (keyword root,
  image hash, username similarity, name overlap, OCR overlap, reverse
  match); click nodes to inspect, toggle signals per type
- **New Scan** `/new-scan` — run a scan from the browser with live
  progress and graceful stop

Scans started from the dashboard run as isolated subprocesses
(`social_osint.py`), so a scan crash never takes down the server.
Progress is read from `scan_status.json` written atomically by the
scanner.

Port can be changed with `OSINT_DASHBOARD_PORT` (default `8000`; port
5000 is avoided because macOS AirPlay occupies it).

## Authentication

Login is **enabled by default**. Default credentials on first start:
`admin` / `admin123` — **change it after login** (navbar → Change
Password) or via environment configuration.

Credentials are resolved in order:

1. `OSINT_DASHBOARD_USERS_FILE` — multi-user YAML file
   (`config/users.yaml`, see `config/users.yaml.example`)
2. `output/.dashboard_users.yaml` — persisted changes (change-password)
3. `config/users.yaml`
4. `OSINT_DASHBOARD_USER` + `OSINT_DASHBOARD_PASSWORD` (or
   `OSINT_DASHBOARD_PASSWORD_HASH`) — single user
5. default `admin` / `admin123` (persisted, warning printed at startup)

Passwords are stored as werkzeug hashes — never plaintext. Generate a
hash with:

```bash
python -m dashboard.auth hash "your-password"
```

Session secret: `OSINT_DASHBOARD_SECRET_KEY` (default: persisted in
`output/.dashboard_secret`).

## Reports (generate / export)

- **Printable report** — `/reports/<session>` (Print button → PDF via
  browser print)
- **JSON download** — `GET /api/reports/<session>/download`
- **CSV export** — `GET /api/reports/<session>/export.csv`

Buttons are available in Sessions, Profiles, and the Dashboard page.

## Docker

```bash
docker compose up --build
# open http://localhost:8000
```

Reports persist in the `output/` volume. Environment overrides
(`.env.example`): `OSINT_REGION`, `OSINT_MAX_RESULTS`,
`OSINT_OCR_ENABLED`, `OSINT_LEET_VARIANTS`.

## Configuration

```text
config/config.yaml      search, browser, collector, ocr, output
config/platforms.yaml   platform domains + enabled flags
config/scoring.yaml     risk weights, levels, image match thresholds
```

Environment variables override YAML values (see `.env.example`).

## Tests

```bash
python -m pytest tests/ -q
```

Unit tests never require network access. Legacy behavior is captured in
characterization/regression suites; the refactor must not regress the
legacy fields `url, account_names, keyword_detected, profile_image,
image_hash, ocr_text, reverse_image_match, risk_score`.

## Report Schema

```json
{
  "schema_version": "1.0",
  "scan_id": "session_20260818_161910",
  "target": "anugan",
  "started_at": "", "completed_at": "",
  "statistics": {"discovered": 0, "analyzed": 0, "matched": 0},
  "profiles": [],
  "connections": []
}
```

Legacy bare-array reports are still read by the dashboard.

Profiles that fail to analyze are kept in the report with
`"analyze_status": "failed"` and `"analyze_error"` — discovered profiles
never silently disappear.

## Structure

```text
config/          YAML configuration (config, platforms, scoring)
core/            models, config loader, logger, scanner API, factory
discovery/       search engine, query builder, deduplicator
collectors/      http client, playwright client, image downloader
analyzers/       profile analyzer, extraction, image, OCR
correlation/     username matcher, image matcher, entity linker
scoring/         risk engine
storage/         json storage, report manager
utils/           normalization, hashing, validators
dashboard/       Flask dashboard (view + trigger scans + link analysis)
tests/           unit tests (no network)
```

## GitHub Actions

Push to GitHub — CI runs `pytest` and builds the Docker image on every
push/PR (`.github/workflows/ci.yml`).

## Template & Credits

Dashboard UI adapted from **dashdarkX-v1.0.0** — a free React admin
dashboard template by ThemeWagon (MIT license,
https://github.com/themewagon/dashdarkX). Design tokens (colors,
typography, layout patterns) were ported to a standalone CSS layer
(`dashboard/static/css/dashdarkx.css`); the React template source is not
a runtime dependency. Earlier iterations used Product Admin (templatemo
tm-524) and Datta Able (CodedThemes) as visual references.
