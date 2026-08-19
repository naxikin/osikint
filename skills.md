# Social OSINT — OpenCode Skills

## 1. Project Identity

Project: `Social OSINT`

Primary file:

```text
social_osint.py
```

The existing `social_osint.py` is the behavioral baseline.

Current implementation includes:

* Search-engine discovery
* Social platform targeting
* Username/text normalization
* Leetspeak normalization
* Fuzzy matching
* URL deduplication
* Dynamic page collection with Playwright
* HTML parsing with BeautifulSoup
* Profile-name extraction
* OpenGraph image extraction
* Image downloading
* Image hashing
* OCR
* Profile analysis
* Reverse image correlation
* Risk scoring
* JSON autosave
* Ctrl+C partial-result handling
* CLI execution

The existing implementation must be treated as the source of truth for backward-compatible behavior.

---

# 2. Primary Objective

Refactor and improve the existing Social OSINT implementation while preserving its existing behavior.

The target architecture must be:

```text
Discovery
    ↓
Collection
    ↓
Extraction
    ↓
Normalization
    ↓
Matching
    ↓
Image/OCR Analysis
    ↓
Correlation
    ↓
Risk Scoring
    ↓
Storage
    ↓
CLI / Dashboard
```

The project must become:

* modular
* testable
* maintainable
* deterministic
* configurable
* fault tolerant
* backward compatible

---

# 3. Non-Negotiable Rule

## DO NOT blindly rewrite `social_osint.py`

Before modifying the implementation:

1. Read the complete file.
2. Identify every function.
3. Identify global variables.
4. Identify external dependencies.
5. Identify CLI behavior.
6. Identify output fields.
7. Identify network operations.
8. Identify error handling.
9. Create regression/characterization tests.
10. Refactor incrementally.

Never change multiple architectural layers at once without tests.

---

# 4. Existing Functional Baseline

The current source contains these major functions:

```text
normalize_text()
similarity()
contains_keyword()
save_results()
signal_handler()
search_social_accounts()
fetch_dynamic_page()
extract_account_names()
extract_profile_image()
download_image()
calculate_image_hash()
extract_text_from_image()
analyze_profile()
```

The current CLI flow:

```text
Target keyword
      ↓
Search social accounts
      ↓
Discovered profiles
      ↓
Analyze each profile
      ↓
Autosave results
      ↓
Final JSON report
```

---

# 5. Current Platform Targets

The implementation targets:

```text
instagram.com
facebook.com
x.com
tiktok.com
github.com
linkedin.com
gitlab.com
```

The platform list must be configurable.

Recommended configuration:

```yaml
platforms:
  instagram:
    domain: instagram.com
    enabled: true

  facebook:
    domain: facebook.com
    enabled: true

  x:
    domain: x.com
    enabled: true

  tiktok:
    domain: tiktok.com
    enabled: true

  github:
    domain: github.com
    enabled: true

  linkedin:
    domain: linkedin.com
    enabled: true

  gitlab:
    domain: gitlab.com
    enabled: true
```

Do not concatenate platform domains accidentally.

---

# 6. Normalization Engine

The existing implementation performs leetspeak normalization.

Current mappings:

```text
4 → a
@ → a
3 → e
1 → i
! → i
0 → o
$ → s
5 → s
7 → t
```

The normalized representation must not replace the original value.

Always preserve:

```json
{
  "original": "M@l4k4j!___",
  "normalized": "malakaji"
}
```

Recommended API:

```python
normalize_text(text: str) -> str
```

and:

```python
normalize_identifier(text: str) -> NormalizedIdentifier
```

---

# 7. Matching Engine

The matching engine must support:

```text
exact
normalized
partial_ratio
sequence_similarity
fuzzy
```

Current behavior uses:

```text
rapidfuzz.partial_ratio
threshold = 80
```

Preserve this behavior unless explicitly instructed otherwise.

Recommended result:

```json
{
  "matched": true,
  "method": "partial_ratio",
  "score": 91,
  "target": "malakaj",
  "candidate": "M@l4k4j!"
}
```

Do not expose only boolean results internally.

---

# 8. Search Discovery

The discovery engine must support query generation based on:

```text
exact keyword
URL
title
site
normalized keyword
```

Existing query patterns:

```text
"{keyword}" site:{site}
inurl:{keyword} site:{site}
intitle:"{keyword}" site:{site}
```

Separate:

```text
query_builder
search_engine
result_parser
deduplicator
```

Do not place all search functionality in one function.

---

# 9. Search Result Model

Every discovered result should use a structured model:

```python
@dataclass
class SearchResult:
    title: str
    url: str
    body: str
    source: str
```

Example:

```json
{
  "title": "Example Profile",
  "url": "https://example.com/profile",
  "body": "Public profile description",
  "source": "example.com"
}
```

---

# 10. URL Deduplication

URLs must be deduplicated.

Use canonicalization before comparison.

Consider:

```text
http / https
trailing slash
fragment
tracking parameters
URL encoding
```

Do not modify meaningful URL path components.

---

# 11. Web Collection

Implement two collectors:

```text
HTTPCollector
PlaywrightCollector
```

Preferred strategy:

```text
HTTP
  ↓
Is content sufficient?
  ├── YES → continue
  └── NO
        ↓
    Playwright
```

Do not use Playwright unnecessarily.

---

# 12. Playwright

The existing implementation uses:

```text
headless browser
custom User-Agent
viewport
locale
networkidle
60-second timeout
```

Maintain configurable browser settings.

Recommended:

```yaml
browser:
  headless: true
  timeout: 60000
  locale: en-US
  viewport:
    width: 1920
    height: 1080
```

Do not implement mechanisms intended to bypass:

* authentication
* CAPTCHA
* access controls
* rate limits
* security controls

Only process content that is publicly accessible and lawfully available.

---

# 13. Profile Extraction

Extract:

```text
page title
OpenGraph title
Twitter title
H1
H2
H3
OpenGraph image
page text
final URL
```

Recommended result:

```json
{
  "account_names": [],
  "profile_image": null,
  "page_text": "",
  "final_url": ""
}
```

Extraction must be independent from scoring.

---

# 14. Profile Analyzer

The profile analyzer orchestrates:

```text
fetch
    ↓
parse
    ↓
extract names
    ↓
match keyword
    ↓
extract image
    ↓
download image
    ↓
calculate hash
    ↓
OCR
    ↓
image correlation
    ↓
risk scoring
```

It must not contain low-level implementation for every operation.

Instead use injected services:

```python
ProfileAnalyzer(
    collector=...,
    extractor=...,
    matcher=...,
    image_analyzer=...,
    ocr_engine=...,
    correlation_engine=...,
    risk_engine=...
)
```

---

# 15. Image Pipeline

Current implementation:

```text
profile image URL
      ↓
download
      ↓
PIL
      ↓
average hash
      ↓
OCR
      ↓
known hash correlation
```

Maintain this behavior during initial refactoring.

Then extend to:

```text
SHA-256
aHash
dHash
pHash
OCR
perceptual similarity
```

---

# 16. Deterministic Image Identification

DO NOT use Python's built-in:

```python
hash(url)
```

for persistent filenames or identifiers.

Use deterministic hashing:

```python
hashlib.sha256(url.encode("utf-8")).hexdigest()
```

or:

```python
hashlib.sha256(image_bytes).hexdigest()
```

The same input must produce the same identifier across processes.

---

# 17. OCR Engine

OCR must be isolated from profile analysis.

Interface:

```python
class OCREngine:
    def extract_text(self, image_path: str) -> OCRResult:
        ...
```

Result:

```json
{
  "text": "detected text",
  "engine": "tesseract",
  "confidence": null
}
```

OCR failure must not terminate the scan.

---

# 18. Image Correlation

Image matching is a correlation signal.

Never describe an image match as proof of identity.

Supported states:

```text
NO_MATCH
POSSIBLE_MATCH
PROBABLE_MATCH
HIGH_SIMILARITY
```

Example:

```json
{
  "matched": true,
  "method": "phash",
  "distance": 4,
  "similarity": 0.94
}
```

Correlation must retain evidence.

---

# 19. Entity Correlation

The framework should support multiple independent signals:

```text
username
normalized username
profile name
URL
image hash
OCR
metadata
```

Each signal must produce structured evidence:

```json
{
  "signal": "username_similarity",
  "score": 0.91,
  "confidence": "high",
  "evidence": "M@l4k4j!"
}
```

Never collapse all signals into an unexplained boolean.

---

# 20. Risk Engine

Current risk logic uses:

```text
keyword detected      +4
OCR keyword detected  +5
reverse image match   +6
```

These values must remain compatible with the existing implementation.

Move configuration to:

```yaml
risk:
  keyword_detected: 4
  ocr_detected: 5
  reverse_image_match: 6
```

Recommended result:

```json
{
  "score": 10,
  "level": "medium",
  "factors": [
    {
      "name": "keyword_detected",
      "weight": 4
    }
  ]
}
```

The score represents an analytical signal only.

It must not automatically label a person as malicious.

---

# 21. JSON Storage

The current implementation performs atomic temporary-file writing:

```text
report.json.tmp
      ↓
os.replace()
      ↓
report.json
```

Preserve this behavior.

Storage API:

```python
save_results(results, output_file)
```

must remain available during migration.

---

# 22. Report Schema

Use versioned reports:

```json
{
  "schema_version": "1.0",
  "scan_id": "session_20260818_154500",
  "target": "keyword",
  "started_at": "",
  "completed_at": "",
  "statistics": {
    "discovered": 0,
    "analyzed": 0,
    "matched": 0
  },
  "profiles": []
}
```

Each profile must preserve legacy fields:

```text
url
account_names
keyword_detected
profile_image
image_hash
ocr_text
reverse_image_match
risk_score
```

Do not remove legacy fields without an explicit migration plan.

---

# 23. Autosave

Autosave must occur after each successfully analyzed profile.

Required behavior:

```text
Profile 1
  ↓
save

Profile 2
  ↓
save

Profile 3
  ↓
save
```

If the application crashes after profile 3, profiles 1–3 must remain in the report.

---

# 24. Ctrl+C

The current application supports:

```text
SIGINT
Ctrl+C
partial result save
clean exit
```

Preserve this behavior.

Expected flow:

```text
[CTRL+C DETECTED]
[SAVING PARTIAL RESULTS]
[REPORT SAVED]
```

Never discard already completed results.

---

# 25. Error Handling

Do not use:

```python
except:
    pass
```

Replace with explicit handling.

Bad:

```python
try:
    ...
except:
    return None
```

Better:

```python
try:
    ...
except requests.RequestException as exc:
    logger.warning("Request failed: %s", exc)
    return None
```

A failed profile must not terminate the entire scan.

---

# 26. Logging

Use a logger instead of business-logic `print()` calls.

Levels:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

CLI can retain colored output.

Logging must not expose:

```text
passwords
cookies
tokens
authorization headers
private credentials
```

---

# 27. Configuration

Create:

```text
config/
├── config.yaml
├── platforms.yaml
└── scoring.yaml
```

Centralize:

```text
search region
result limits
fuzzy thresholds
browser timeout
OCR enable/disable
image analysis
risk weights
autosave
output location
```

Do not hard-code tunable values.

---

# 28. Recommended Project Structure

Target:

```text
social-osint/
│
├── social_osint.py
├── skills.md
├── README.md
├── pyproject.toml
├── .gitignore
│
├── config/
│   ├── config.yaml
│   ├── platforms.yaml
│   └── scoring.yaml
│
├── core/
│   ├── models.py
│   ├── config.py
│   ├── logger.py
│   ├── exceptions.py
│   └── session.py
│
├── discovery/
│   ├── search_engine.py
│   ├── query_builder.py
│   └── deduplicator.py
│
├── collectors/
│   ├── http_client.py
│   ├── playwright_client.py
│   └── image_downloader.py
│
├── analyzers/
│   ├── profile_analyzer.py
│   ├── username_analyzer.py
│   ├── metadata_analyzer.py
│   ├── image_analyzer.py
│   └── ocr_analyzer.py
│
├── correlation/
│   ├── username_matcher.py
│   ├── image_matcher.py
│   └── entity_linker.py
│
├── scoring/
│   └── risk_engine.py
│
├── storage/
│   ├── json_storage.py
│   └── report_manager.py
│
├── utils/
│   ├── normalization.py
│   ├── hashing.py
│   └── validators.py
│
├── output/
│
└── tests/
    ├── test_normalization.py
    ├── test_matching.py
    ├── test_discovery.py
    ├── test_collectors.py
    ├── test_image.py
    ├── test_ocr.py
    ├── test_correlation.py
    ├── test_scoring.py
    └── test_storage.py
```

---

# 29. Testing

Create tests BEFORE major refactoring.

Minimum tests:

```text
test_normalize_text
test_similarity
test_contains_keyword
test_query_generation
test_url_deduplication
test_json_save
test_atomic_save
test_ctrl_c_save
test_image_hash
test_ocr_failure
test_risk_score
test_profile_result_schema
```

Network access must not be required for unit tests.

Use mocks and fixtures.

---

# 30. Characterization Tests

Before refactoring, capture representative legacy behavior.

Example:

```python
def test_legacy_normalization():
    assert normalize_text("M@l4k4j!___") == "malakaji"
```

Capture representative:

```text
keyword
username variants
URLs
search results
profile extraction
risk score
JSON output
```

The refactored implementation must be compared against these results.

---

# 31. Regression Testing

For the same input:

```text
legacy implementation
        VS
refactored implementation
```

Compare:

```text
URL
account_names
keyword_detected
profile_image
image_hash
ocr_text
reverse_image_match
risk_score
```

Any difference must be investigated.

Do not silently accept regression.

---

# 32. CLI Compatibility

This command must continue working:

```bash
python social_osint.py
```

Interactive prompt:

```text
Target keyword:
```

Optional CLI arguments may be added:

```bash
python social_osint.py --target "keyword"
python social_osint.py --output output/
python social_osint.py --config config/config.yaml
python social_osint.py --platform github
python social_osint.py --verbose
```

Existing behavior must remain available.

---

# 33. Dependencies

Declare dependencies explicitly.

Expected dependencies:

```text
requests
pytesseract
Pillow
beautifulsoup4
colorama
rapidfuzz
ddgs
playwright
pytest
PyYAML
ImageHash
```

Do not introduce unnecessary dependencies.

After dependency changes:

```bash
pip install -r requirements.txt
```

or the project's package manager must be updated accordingly.

---

# 34. Python Quality

Use:

```text
PEP 8
type hints
dataclasses where appropriate
small functions
single responsibility
explicit exceptions
dependency injection
structured logging
```

Avoid:

```text
global mutable state
duplicated logic
magic numbers
silent exceptions
unused imports
dead code
```

---

# 35. Security Rules

This framework is for lawful OSINT, research, defensive security, and authorized investigations.

The implementation must NOT add functionality for:

* credential theft
* account takeover
* authentication bypass
* CAPTCHA bypass
* unauthorized private-data access
* covert tracking
* exploitation of accounts
* malware deployment
* unauthorized surveillance
* bypassing access controls

Only process information that is publicly accessible and lawfully available.

Respect applicable:

```text
laws
privacy requirements
platform terms
rate limits
robots policies where applicable
```

---

# 36. Privacy

Minimize collection of personal information.

Do not unnecessarily store:

```text
passwords
authentication cookies
session tokens
private messages
private account information
```

Support configurable redaction where practical.

Example:

```yaml
privacy:
  redact_sensitive_data: true
  redact_email: false
  redact_phone: false
```

---

# 37. Performance

Preferred pipeline:

```text
Discovery
   ↓
Deduplication
   ↓
Cheap matching
   ↓
HTTP collection
   ↓
Playwright only if necessary
   ↓
Profile extraction
   ↓
Image analysis
   ↓
OCR
   ↓
Correlation
   ↓
Risk scoring
   ↓
Autosave
```

Do not perform OCR when OCR is disabled.

Do not download duplicate images unnecessarily.

Cache reusable resources where safe.

---

# 38. Concurrency

Concurrency may be introduced after functional parity is established.

First achieve:

```text
correctness
↓
test coverage
↓
modularity
↓
performance
```

Do not introduce concurrency before regression tests exist.

When adding concurrency:

* respect rate limits
* limit worker count
* handle timeouts
* handle retries carefully
* maintain deterministic result ordering where required
* preserve autosave integrity

---

# 39. Code Modification Protocol

When OpenCode receives a development task:

## Step 1

Inspect the relevant files.

## Step 2

Identify dependencies.

## Step 3

Check existing tests.

## Step 4

Create or update tests.

## Step 5

Implement the smallest safe change.

## Step 6

Run tests.

## Step 7

Run static checks.

## Step 8

Inspect the diff.

## Step 9

Verify backward compatibility.

## Step 10

Document the change.

Never make unrelated modifications.

---

# 40. Bug Fix Protocol

For every bug:

```text
Reproduce
   ↓
Create regression test
   ↓
Fix
   ↓
Run test
   ↓
Run full suite
```

Never fix a bug without a regression test when practical.

---

# 41. Known Issues To Inspect

OpenCode must inspect the platform list carefully.

The source contains:

```python
"linkedin.com"
"gitlab.com"
```

without an explicit separator between those entries.

Verify that these become two independent platform entries:

```python
"linkedin.com",
"gitlab.com",
```

Also inspect image filenames generated using Python's built-in `hash()`.

Replace persistent use of:

```python
hash(profile_image)
```

with deterministic hashing.

Inspect all occurrences of:

```python
except:
```

and replace silent exception handling.

---

# 42. Output Compatibility

The current profile result contains:

```json
{
  "url": "...",
  "account_names": [],
  "keyword_detected": false,
  "profile_image": null,
  "image_hash": null,
  "ocr_text": "",
  "reverse_image_match": false,
  "risk_score": 0
}
```

These fields must remain available.

Additional fields may be added without removing legacy fields.

Recommended additional fields:

```json
{
  "platform": "",
  "original_url": "",
  "final_url": "",
  "match_details": {},
  "image_analysis": {},
  "ocr_analysis": {},
  "correlation": {},
  "risk_details": {}
}
```

---

# 43. Future Dashboard Compatibility

The architecture should allow a future dashboard to consume the JSON report.

Dashboard requirements may include:

```text
summary
profile table
search
filter
risk distribution
correlation graph
profile detail
image evidence
OCR evidence
JSON viewer
scan progress
```

Do not couple the core OSINT engine directly to a dashboard framework.

Expose structured Python APIs and JSON reports instead.

---

# 44. API Boundary

The core application should eventually expose:

```python
class OSINTScanner:

    def discover(self, target: str):
        ...

    def analyze(self, profile):
        ...

    def scan(self, target: str):
        ...

    def save_report(self, report):
        ...
```

CLI and dashboard should call this service.

Architecture:

```text
             ┌─────────────┐
             │     CLI     │
             └──────┬──────┘
                    │
             ┌──────▼──────┐
             │ OSINTScanner│
             └──────┬──────┘
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
 Discovery      Analyzer      Storage
```

---

# 45. Definition of Done

A refactoring task is complete only when:

* [ ] Existing CLI works.
* [ ] Existing output fields remain available.
* [ ] Tests exist.
* [ ] Regression tests pass.
* [ ] Discovery is modular.
* [ ] Collection is modular.
* [ ] Extraction is modular.
* [ ] Matching is modular.
* [ ] Image analysis is modular.
* [ ] OCR is modular.
* [ ] Correlation is modular.
* [ ] Risk scoring is configurable.
* [ ] JSON storage is atomic.
* [ ] Autosave works.
* [ ] Ctrl+C works.
* [ ] No silent `except:` remains.
* [ ] Persistent hashes are deterministic.
* [ ] Platform configuration is correct.
* [ ] GitLab is a separate platform.
* [ ] No credentials are stored.
* [ ] No unauthorized access functionality is introduced.
* [ ] Documentation is updated.

---

# 46. Final Engineering Principle

Always prioritize:

```text
Correctness
    >
Backward Compatibility
    >
Testability
    >
Maintainability
    >
Performance
    >
New Features
```

The goal is not merely to produce a new implementation.

The goal is to transform the existing Social OSINT script into a reliable modular framework while preserving its established behavior.

**Never sacrifice existing functionality merely to make the architecture cleaner.**
