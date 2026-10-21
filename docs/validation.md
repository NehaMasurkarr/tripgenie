# Validation scope

Local checks were run on October 11, 2026. The [first full CI run](https://github.com/NehaMasurkarr/tripgenie/actions/runs/38193575998) passed backend, Flutter, and real-browser integration jobs. Two additional internal-error cases were subsequently validated locally; see [GitHub Actions](https://github.com/NehaMasurkarr/tripgenie/actions/workflows/ci.yml) for remote run status; configuration alone is not proof of a passing run.

| Check | Tested scope |
|---|---|
| Python tests | 62 passing model, evaluation, API, input/error/CORS, grounding, exclusion, and integrity checks. |
| Fresh setup | Dependency installation, 62 tests, and `pip check` passed in a clean temporary Python 3.13 environment; the project environment uses Python 3.12. |
| Notebooks | All five executed in temporary copies: 12 + 8 + 7 + 6 + 4 = 37 successful code cells. Original notebook/data checksums remained unchanged. |
| Flutter | Formatting, static analysis with no issues, and ten passing HTTP client/widget tests. |
| Responsive layouts | Widget tests at 390, 768, and 1440 px; errors, retry, empty matches, budget validation, and itinerary rendering checked. |
| Release build | Flutter 3.35.4/Dart 3.9.2 web build passed with locally bundled CanvasKit/resources. |
| Live API | Actual Gunicorn HTTP requests verified readiness, options, discovery, five distinct recommendations, contribution arithmetic, and a three-day grounded itinerary. |
| Browser integration | Real Chromium discovery search, preference editing, five unique scored matches, and itinerary requests at desktop/mobile widths. No mocked HTTP responses in this harness. |

Automated browser testing enables Flutter semantics and waits for the native editor focus handoff before keyboard input. The harness asserts that a changed daily budget is actually transmitted, rather than accepting a screenshot of a changed field. Screenshots are smoke artifacts, not pixel-perfect golden tests or a complete accessibility audit.

## Limits of verification

- Android SDK is absent; Xcode is older than Flutter's recommended minimum and CocoaPods is absent. Native Android/iOS builds, signing, installation, and network permissions have not been validated.
- No production-scale load test, public deployment, authentication, bookings, live travel-data integration, offline catalogue API, or persistent saved trips is claimed.
- Model metrics are weak-label and synthetic-profile proxies. No real user ratings, interaction data, or independent traveler relevance judgments are available. Timing is local sequential warm-model timing.
- The pre-existing uncommitted edit in `notebooks/02_data_preprocessing.ipynb` removes introductory Markdown only. It was reviewed, preserved byte-for-byte, validated via a temporary copy, and excluded from implementation commits.
- Application requests and evaluation do not change original/processed dataset JSONs. All recommendation/model state is memory-local to the running worker/session.

## Repeat checks

Use [root setup instructions](../README.md), [Flutter setup](../frontend/README.md), and [API reference](api.md). Run `python -m pytest -q`, `python scripts/validate_notebooks.py`, `flutter analyze`, and `flutter test`. To run the real-browser flow, start the API on 5001 and the compiled frontend on 5173, install Playwright/Chromium, then run `python scripts/browser_smoke.py` from the root. The workflow performs the same service flow in CI.
