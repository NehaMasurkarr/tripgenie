# TripGenie Flutter client

Responsive destination discovery, preference selection, explainable recommendations, and catalogue-grounded itinerary views. The client uses typed models and a reusable HTTP service with loading, retry, error, and empty states. No API key or account is needed locally. Decorative landscapes are code-drawn illustrations.

## Run locally

Start the API from the repository root in a separate terminal:

```sh
source .venv/bin/activate
python -m flask --app backend.app:create_app run --host 127.0.0.1 --port 5001
```

Then, from this directory:

```sh
flutter pub get --enforce-lockfile
flutter run -d chrome --web-port 5173 --dart-define=API_BASE_URL=http://127.0.0.1:5001
```

Validated with Flutter 3.35.4 / Dart 3.9.2. `API_BASE_URL` is a build-time public URL, not a secret. Changing it requires restarting/rebuilding the app. The backend's `TRIPGENIE_ALLOWED_ORIGINS` must contain the exact frontend origin (scheme, host, port).

## Checks and release web build

```sh
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test --reporter expanded
flutter build web --release --no-web-resources-cdn --dart-define=API_BASE_URL=http://127.0.0.1:5001
python3 -m http.server 5173 --bind 127.0.0.1 --directory build/web
```

Ten client/widget tests cover JSON decoding, preferences, errors, timeouts, retry, empty results, form validation, itinerary rendering, and 390/768/1440 px layouts. HTTP fixtures are snapshots generated from the actual API and are intentionally used only in isolated tests. [Browser smoke testing](../scripts/browser_smoke.py) drives the release web app against a real running backend with no mocked responses.

## Native platforms

Android/iOS project scaffolds are included, but native builds/signing were not verified in this environment (Android SDK missing; Xcode outdated and CocoaPods absent). Responsive mobile **web** behavior is tested. For an Android emulator, a local host API usually uses `http://10.0.2.2:5001`; the debug Android manifest permits local HTTP. A physical device needs a reachable API address; production builds should use HTTPS. Set the URL with `--dart-define=API_BASE_URL=...`. Install the platform toolchains and validate native networking/builds before shipping.

Preferences and the current itinerary stay in memory for the current session. There is no account, persistent trip storage, booking, live map routing, or offline API mode. Dataset-derived scores are not suitability guarantees, and costs/conditions require confirmation before booking.
