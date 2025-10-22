OpenPlantbook SDK — Project Guidelines for Advanced Contributors

This document captures project-specific knowledge to speed up onboarding and reduce friction when developing, testing, and releasing changes to this repository.

1. Build and Configuration
- Runtime: Python 3.9+ (project metadata enforces >=3.9). Use the same minor version locally to avoid subtle typing/stdlib differences.
- Install dependencies:
  - Library runtime deps are defined in setup.cfg (install_requires: aiohttp, json-timeseries).
  - Dev/test utilities used in this repo’s tests: numpy, pandas, PyYAML, tabulate (see requirements.txt at repo root). For a full dev setup:
    - pip install -r requirements.txt
    - Optional: pip install -e . (editable install) when working across multiple local projects consuming this SDK.
- Configuration for integration tests:
  - The test suite reads Open Plantbook API credentials from config.yaml in the repository root. A template is provided in config.yaml.dist.
  - Keys expected by tests (tests/test_openplantbook_sdk.py):
    - client_id: string (from https://open.plantbook.io)
    - secret: string (client secret)
    - base_url: optional; defaults to https://open.plantbook.io/api/v1 when omitted
  - To run tests that hit the real API: copy config.yaml.dist to config.yaml and fill in your credentials.

2. Testing
- Test frameworks: The existing suite uses Python’s unittest API but can be run via either unittest or pytest. pytest will happily discover unittest.TestCase tests.
- Running tests:
  - With pytest: pytest -q
  - With unittest: python -m unittest discover -s tests -p "test_*.py"
- Networked tests:
  - tests/test_openplantbook_sdk.py makes live calls to Open Plantbook. Valid credentials are mandatory. These tests will fail (or hang due to HTTP 401/403) without config.yaml.
  - Rate limiting and availability: be mindful of API rate limits and quota. Prefer dry-run flags when available (e.g., async_plant_data_upload has dry_run=True option) and keep payload sizes modest.
- Adding new tests:
  - Prefer isolating business logic from I/O so that most tests run offline. For async HTTP, factor out small pure functions or inject clients.
  - For aiohttp usage, mock at the boundary:
    - Patch aiohttp.ClientSession to return a pre-canned response. With pytest, use monkeypatch; with unittest, use unittest.mock.patch.
    - Consider parametrizing base_url to point to a local fake server for contract tests.
  - Configuration access in tests should go through a helper that is tolerant to missing config.yaml (e.g., skip networked tests when creds are absent).
- Demonstration test (local/offline example):
  - A minimal smoke test can verify module import and basic construction without touching the network:
    - from openplantbook_sdk import OpenPlantBookApi
    - api = OpenPlantBookApi("id", "secret", base_url="https://example.invalid")
    - assert api.client_id == "id" and api.secret == "secret"
  - This pattern is useful to confirm packaging/imports work in CI where credentials are intentionally absent. Do not call async methods in such tests.
- Running only offline tests:
  - Use markers or filename patterns (e.g., keep offline tests in tests/offline/) and select with pytest -k offline or -k "not network" depending on how you annotate.

3. Development Notes and Pitfalls
- Async model:
  - The SDK is asynchronous (aiohttp). Public methods are async_* and are intended to be awaited. The tests use asyncio.run(...). When embedding in an already-running event loop (e.g., in async apps), prefer await api.async_... directly. Avoid nested asyncio.run in async contexts.
  - Token handling: _async_get_token caches an OAuth token in self.token and refreshes when <5 minutes remaining. It will raise MissingClientIdOrSecret if client_id/secret are absent before checking the cache.
- Error handling and validation:
  - OpenPlantBookApi methods log and either raise or return None on errors (see sdk.py for method-specific behavior). Network exceptions are mapped from aiohttp exceptions and logged for triage.
  - ValidationError is raised for API validation responses; inspect .errors for structured details in tests.
- Data layer:
  - json_timeseries (a.k.a. json-timeseries on PyPI) provides TimeSeries, TsRecord, JtsDocument used by async_plant_data_upload. See tests/test_openplantbook_sdk.py for a realistic usage pattern, including TimeSeries insertion and JtsDocument aggregation.
- Code style and quality:
  - Follow PEP 8. The project does not enforce a formatter in CI here, but black with default settings is acceptable. Keep import order stdlib, third-party, local.
  - Keep logging via the module-level _LOGGER in sdk.py; prefer debug for routine HTTP events and error for failures.
- Docs:
  - Sphinx project is under docs/. You can build it with:
    - pip install -r docs/requirements.txt
    - On Windows: .\docs\make.bat html
    - On POSIX: make -C docs html

4. Practical Workflows
- Local development loop:
  - Create/activate a Python 3.9+ virtual environment.
  - pip install -r requirements.txt
  - Optional: pip install -e .
  - If you will run networked tests: copy config.yaml.dist to config.yaml and fill credentials.
  - Run offline tests first (fast feedback). Then run networked tests selectively.
- Releasing:
  - pyproject.toml and setup.cfg contain packaging metadata; versions are bumped in setup.cfg. Wheels/tarballs under dist/ are artifacts and not used for building during development.

5. Troubleshooting
- ImportError for json_timeseries vs json-timeseries:
  - The import in code is from json_timeseries import ... while the package name on PyPI can be json-timeseries. Use requirements and setup.cfg as authoritative; ensure the correct package is installed.
- HTTP errors:
  - 401/403 usually indicate invalid credentials in config.yaml. Verify client_id/secret and whether the token endpoint is reachable from your network.
  - TooManyRedirects or ServerTimeoutError are surfaced and logged; consider checking base_url correctness or retry policies.
- Timezone-sensitive data:
  - Upload tests use tz-aware timestamps (e.g., Australia/Sydney). Keep records tz-aware; JtsDocument should handle ISO-8601 with offsets.

6. CI Hints
- If you wire this repo into CI without secrets, skip networked tests by default. For pytest, you can conditionally mark/skip based on the presence of config.yaml and required keys.
- Keep one smoke test (import/construct) to validate packaging across Python versions.

Appendix — Test Execution Example (manual)
- Offline:
  - pytest -q -k "smoke or offline"
- Online (requires config.yaml with real creds):
  - pytest -q tests/test_openplantbook_sdk.py
