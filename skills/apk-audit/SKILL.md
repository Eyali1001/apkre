---
trigger: security audit APK|audit Android app|APK security|find unauthenticated endpoints|Android security audit|APK pentest|mobile app audit
---

# APK Security Audit

A structured workflow for security-auditing Android applications. Downloads the APK, decompiles it, extracts all API endpoints, analyzes authentication, identifies unauthenticated endpoints, runs live PoC tests, and produces a structured report.

## Prerequisites

Dependencies are checked and auto-installed at the start of each audit. Run manually if needed:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-deps.sh
bash ${CLAUDE_PLUGIN_ROOT}/scripts/install-dep.sh <dep>
```

Required: apkeep, jadx, Java 17+, uv. Optional: vineflower, dex2jar.

## Workflow

### Phase 0: Resolve App Description

If the user provides a natural-language description instead of a package name or file path (e.g. "the israeli parking app", "Domino's Pizza Israel"):

1. **Search the web** for the app on Google Play:
   ```
   WebSearch: "<description>" site:play.google.com
   ```
2. Extract the package name from the Google Play URL (`id=` parameter).
3. If multiple candidates match, present them to the user and ask which one to audit.
4. Once confirmed, continue to Phase 1 with the resolved package name.

### Phase 1: Setup & Download

If starting from a package name (not an existing file):

1. Create a working directory for the app:
   ```bash
   mkdir -p <appname>
   ```

2. Download the APK using apkeep:
   ```bash
   apkeep -a <package.name> ./<appname>/
   ```

   > Find the package name from the Google Play URL: `play.google.com/store/apps/details?id=<package.name>`

   This produces an `.xapk` (split APK bundle) or `.apk` file inside the directory.

If starting from an existing file, skip to Phase 2.

### Phase 2: Decompile & Initial Exploration

This phase delegates to the bundled [android-reverse-engineering-skill](https://github.com/SimoneAvogadro/android-reverse-engineering-skill). **Read and follow its full workflow** — it contains valuable guidance on engine selection, structure analysis, call flow tracing, and handling obfuscated code.

The skill's documentation is at:
- **Full skill**: `${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/plugins/android-reverse-engineering/skills/android-reverse-engineering/SKILL.md`
- **References**: `${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/plugins/android-reverse-engineering/skills/android-reverse-engineering/references/`

Follow Phases 1–5 of their skill (deps → decompile → analyze structure → trace call flows → extract APIs), using their scripts:

```bash
# Scripts are at this base path:
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/plugins/android-reverse-engineering/skills/android-reverse-engineering/scripts"

bash "$SCRIPTS/check-deps.sh"           # Check deps (jadx, java)
bash "$SCRIPTS/install-dep.sh" <dep>    # Install if missing
bash "$SCRIPTS/decompile.sh" <file>     # Decompile
bash "$SCRIPTS/find-api-calls.sh" <output>/sources/  # Find APIs
```

The decompiled output goes to `<package>-decompiled/` in the current working directory.

> **Note for large apps:** Decompilation of apps with 60K+ classes can take 10+ minutes. Start Phase 3 analysis in parallel once jadx reaches ~85%.

### Phase 3: API & Auth Analysis

This phase should use **parallel agents** for efficiency. Launch these searches concurrently:

#### Agent 1: Manifest & Structure
- Parse AndroidManifest.xml for permissions, exported components, deep links
- Map the package structure and identify architecture pattern
- List all Activities, Services, BroadcastReceivers, ContentProviders

#### Agent 2: API Endpoints
Search both native code and JS bundles (for React Native / Capacitor / hybrid apps):
- All HTTP/HTTPS URLs and base URLs
- API path patterns (`/api/`, `/v1/`, `/auth/`, `/graphql`, etc.)
- Request methods, headers, and body formats
- Third-party service URLs and API keys
- GraphQL schemas (check if introspection is enabled)

Use the bundled API search script:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/plugins/android-reverse-engineering/skills/android-reverse-engineering/scripts/find-api-calls.sh <output>/sources/
```

For hybrid apps, also search JS bundles:
```bash
grep -rn 'https\?://[a-zA-Z0-9._/-]*' <output>/resources/assets/
```

#### Agent 3: Auth & Security
- **Login mechanism**: password, OTP, biometric, OAuth, etc.
- **Token type and management**: JWT, session cookies, custom headers
- **Token storage**: SharedPreferences, AsyncStorage, Keychain, etc.
- **Token refresh and expiry handling**
- **SSL certificate pinning**: look for `CertificatePinner`, `TrustManager`, network security config
- **Root/tamper detection**: look for SafetyNet, Play Integrity, root detection libraries
- **OkHttp interceptors**: search for `Interceptor` implementations — these reveal auth header injection, logging, retry logic

Search patterns:
```
clientSecret, Bearer, Authorization, api[_-]?key, CertificatePinner, TrustManager
```

#### Native Libraries (.so) — Crypto Red Flags

Check for native libraries under `lib/` in the decompiled output. List all `.so` files and look for JNI methods loaded via `System.loadLibrary()` or `System.load()` in the Java/Kotlin source.

Run `strings` on each `.so` and search for encryption-related symbols:
```bash
strings <output>/resources/lib/*/*.so | grep -iE 'AES|encrypt|decrypt|cipher|HMAC|SHA256|RSA|sign|verify|secret|key|iv|nonce|pbkdf'
```

**If a native library contains encryption-related functions, this is a red flag.** It often means the app is hiding crypto logic (key derivation, token signing, request encryption) inside native code to make reverse engineering harder. This is worth investigating — the crypto implementation may have weaknesses, hardcoded keys, or custom (broken) schemes.

**Tell the user**: "The app has native libraries with encryption-related symbols. This likely hides key crypto logic from Java-level analysis. I recommend opening these `.so` files in IDA Pro or Ghidra for manual inspection — look for hardcoded keys, weak algorithms, or custom crypto schemes that bypass standard Android APIs."

Include the list of suspicious `.so` files and their crypto-related symbols in the report.

#### Agent 4: Third-Party SDKs
- Firebase, analytics, crash reporting SDKs
- Payment processors
- Ad networks
- Social login providers
- Any exposed API keys or configuration

### Phase 4: Unauthenticated Endpoint Analysis

After mapping all endpoints and the auth system, identify endpoints callable **without** a session token or auth header.

#### How to identify unauthenticated endpoints

1. **Native Android (Retrofit/OkHttp):** Find API interface files — look for `@GET`, `@POST`, `@PUT`, `@DELETE`, `@PATCH` annotations (or their R8-obfuscated equivalents). For each endpoint, check whether the method signature includes an auth header parameter (e.g. `@Header("Authorization")`).

2. **Hybrid apps (Capacitor/Cordova/RN):** Search the JavaScript bundles for fetch/axios calls. Look for patterns like `authHeader: false`, `requiresAuth: false`, or endpoints called before login.

3. **GraphQL:** Check if introspection is enabled for anonymous users. Compare which queries/mutations enforce auth vs. which execute freely.

4. **Cross-reference with interceptors** — check if a global OkHttp interceptor or axios interceptor injects auth headers on **all** requests, or only conditionally.

#### What to look for

- **Data exposure:** Does it return user data, PII, phone numbers, financial info?
- **Enumeration:** Can it enumerate users, phone numbers, or internal resources?
- **Write operations:** Can it create/modify data without auth (spam, abuse)?
- **Rate limiting:** Is there any visible rate-limit or captcha protection?
- **Input validation:** Are parameters validated, or can they be fuzzed?

### Phase 5: Live Testing (PoC)

For findings from static analysis, write Python PoC scripts to confirm. Use the bundled templates as starting points:

```bash
# Run any PoC script with uv (no virtualenv needed)
uv run --with httpx python <appname>/poc_script.py
```

#### Bundled PoC Templates

Adapt these from `${CLAUDE_PLUGIN_ROOT}/scripts/`:

- **`graphql-introspect.py`** — Dump full GraphQL schema (queries, mutations, types, arguments). Use on every GraphQL endpoint found. Run with and without auth tokens.
  ```bash
  uv run --with httpx python ${CLAUDE_PLUGIN_ROOT}/scripts/graphql-introspect.py <graphql-url> [--token <token>]
  ```

- **`test-unauth.py`** — Test a list of endpoints with and without auth. Classifies each as BLOCKED / ERROR / DATA_RETURNED.
  ```bash
  uv run --with httpx python ${CLAUDE_PLUGIN_ROOT}/scripts/test-unauth.py --base-url <url> --endpoints endpoints.json [--token <token>]
  ```

- **`extract-strings-hermes.py`** — Extract all string literals from Hermes bytecode bundles. Finds URLs, API paths, auth headers, config keys.
  ```bash
  uv run python ${CLAUDE_PLUGIN_ROOT}/scripts/extract-strings-hermes.py <bundle.hbc> [--filter-urls]
  ```

- **`check-ssl-pinning.sh`** — Scan decompiled source for SSL pinning implementations.
  ```bash
  bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-ssl-pinning.sh <decompiled-dir>
  ```

#### Common PoC patterns

- **Anonymous login** → get anon token → test authenticated-only endpoints with it
- **GraphQL introspection** → map full schema → test authorization per resolver
- **REST/GraphQL duality** → same operation on both paths, compare auth enforcement
- **Phone/ID enumeration** → differential error responses reveal registered users
- **IDOR** → swap user IDs in authenticated requests
- **Token forgery** → if crypto keys are hardcoded, attempt to forge tokens

> **Do NOT test OTP/SMS endpoints live.** Sending OTP requests triggers real SMS messages to real phone numbers — this is disruptive and potentially costly. Document OTP weaknesses (missing rate limits, brute-force feasibility, enumeration via error codes) from **static analysis only**. Note the finding in the report without live confirmation.

Save all PoC scripts in the `<appname>/` directory.

### Phase 6: Write Report

Generate the final report using the template at `${CLAUDE_PLUGIN_ROOT}/skills/apk-audit/templates/report-template.md`.

Save to `<appname>/<appname>_report.md`.

Fill in every section with findings from Phases 1–5. For the Security Observations table, assign severity levels:

| Severity | Criteria |
|----------|----------|
| CRITICAL | Direct data breach, RCE, auth bypass on sensitive data |
| HIGH | PII exposure, mass enumeration, write without auth |
| MEDIUM | Information disclosure, missing security controls |
| LOW | Minor misconfigurations, debug artifacts |
| INFO | Best-practice recommendations, no direct risk |

## Field-Tested Patterns

Lessons from real-world audits. Check for all of these — they recur across apps.

### REST/GraphQL Duality

When an app exposes both REST and GraphQL endpoints for the same operations, **test both paths**. A REST proxy to a GraphQL backend often has different auth enforcement than the GraphQL server itself. One path may accept anonymous tokens while the other rejects them. Error responses from the proxy can also leak stack traces, internal file paths, and library versions.

### Global Auth Interceptor ≠ Per-Endpoint Security

Many apps inject `Authorization: Bearer` via a single global OkHttp interceptor. This does NOT mean every endpoint is protected — the server may not actually enforce auth on all routes. If you find 50+ endpoints behind a single interceptor with no per-method `@Header` annotations, the real question is: does the **server** enforce auth, or does it trust the client to send it? Test endpoints individually.

Also watch for **multiple OkHttpClient instances** with different interceptor chains — not all requests may go through the auth interceptor (image uploads, analytics, external APIs).

### OTP & SMS Abuse Surface (Static Analysis Only)

Almost every app with SMS-based auth is vulnerable to at least one of:

1. **SMS bombing** — no server-side rate limit on "send OTP" endpoints. Can flood a phone number with SMS at the app's expense.
2. **OTP brute-force** — 4-6 digit codes with no server-side retry limit. Client-side "3 attempts" means nothing. 6-digit OTP = 1M possibilities, testable in minutes without rate limiting.
3. **Phone enumeration** — "send OTP" endpoint returns different error codes/messages for registered vs unregistered numbers. Reveals the app's entire user base.

Assess from decompiled code: Is rate limiting client-side or server-side? Does the error handling differ by registration status? Is there a CAPTCHA (real or hardcoded placeholder)?

> **Do NOT call OTP endpoints live** — this sends real SMS to real people. Document findings from static analysis only.

### Token Storage Red Flags

Check how tokens are stored — this determines ease of token theft on rooted/compromised devices:

| Storage | Security | Found in |
|---------|----------|----------|
| `SharedPreferences` (plaintext) | None — readable on rooted device | Most native apps |
| `AsyncStorage` (plaintext SQLite) | None | React Native apps |
| Capacitor `Preferences` | None — maps to SharedPreferences | Capacitor/hybrid apps |
| `EncryptedSharedPreferences` | Good — uses Android Keystore | Rare |
| `MMKV` (encrypted mode) | Good — if key is secure | Some RN apps |

Search for: `SharedPreferences`, `AsyncStorage`, `MMKV`, `EncryptedSharedPreferences`, `getSharedPreferences`, `PreferenceManager`.

### Hardcoded Secrets — Where to Look

Secrets hide in predictable places:

1. **`BuildConfig`** and **`strings.xml`** — API keys, client secrets
2. **OkHttp interceptors** — hardcoded auth headers, static passwords
3. **Native `.so` libraries** — AES keys, salts (extractable via `strings`)
4. **Bootstrap/config endpoints** — static credentials to fetch dynamic config (the static creds themselves are hardcoded)
5. **JavaScript bundles** — environment configs, API keys in RN/Capacitor apps
6. **`@raw/` resources** — certificates, config files

A common pattern: the app calls a "getConfig" endpoint with a hardcoded username/password to fetch dynamic secrets. The hardcoded creds are the vulnerability.

### GraphQL Introspection as Recon

When GraphQL introspection is enabled in production, it reveals the **entire API surface** — including admin operations the app's UI never calls. Look for mutations named `create`, `delete`, `publish`, `admin`, `accounting`, `internal`. These often lack resolver-level auth checks because developers assumed they'd never be called by clients.

Run the bundled `graphql-introspect.py` on every GraphQL endpoint, with AND without auth tokens.

### Hybrid/Capacitor Apps

Capacitor apps look like native Android but all logic is in JavaScript:
- Minimal Java layer (just `BridgeActivity`)
- All API calls, auth logic, and business logic in JS bundles under `assets/`
- Tokens stored in Capacitor `Preferences` → plaintext SharedPreferences
- `postMessage("*")` for cross-frame token passing → broadcasts to any origin

Search the JS bundle, not the Java source.

### SSL Pinning — Usually Missing

In practice, most apps do NOT implement certificate pinning. Run the bundled `check-ssl-pinning.sh` to verify. If absent, flag it — the app is vulnerable to MITM with a user-installed CA certificate (corporate MDM, rooted device, proxy setup).

Also check for the opposite: custom `TrustManager` implementations that **disable** all certificate validation (accept self-signed certs). Search for `TrustManager`, `X509TrustManager`, `checkServerTrusted`. An empty `checkServerTrusted()` method is a critical finding.

### cleartext Traffic

Search `AndroidManifest.xml` for `android:usesCleartextTraffic="true"` and `network_security_config.xml` for `cleartextTrafficPermitted="true"`. These allow HTTP (not HTTPS) traffic, enabling passive eavesdropping.

## Obfuscated Code Reference

R8/ProGuard obfuscation often renames Retrofit annotations. Common mappings:

| Obfuscated | Original |
|------------|----------|
| `@InterfaceC47949c` | `@GET` |
| `@InterfaceC47958l` | `@POST` |
| `@InterfaceC47962p` | `@Path` |
| `@InterfaceC47963q` | `@Query` |
| `@InterfaceC47967u` | `@Url` |
| `@sy2.bar` | `@Body` |

When encountering obfuscated code, use string literals and library API calls as anchors — URL strings and HTTP method annotations are never fully obfuscated.

## Hermes Bytecode (React Native)

For React Native apps using Hermes:
- Hermes-compiled bundles are bytecode, not readable JS
- Use [hbctool](https://github.com/nicolo-ribaudo/nicolo-ribaudo) or the [hermes96 fork](https://github.com/Hamzamn19/hbctool-hermes96-support) for v96+
- The `string.json` output contains all string literals — URLs, API paths, auth headers, config keys
- For RN apps, API endpoints are in the JS bundle, not in Java/Kotlin Retrofit interfaces

## Project Structure

```
<project>/
├── <appname>/
│   ├── <package>.xapk        ← downloaded APK
│   ├── <appname>_report.md   ← audit report
│   ├── poc_script.py         ← PoC scripts
│   └── ...
└── <package>-decompiled/     ← jadx output (generated by decompile)
    └── <package>/
        ├── resources/
        │   ├── AndroidManifest.xml
        │   └── assets/       ← JS bundles for hybrid apps
        └── sources/          ← decompiled Java/Kotlin
```
