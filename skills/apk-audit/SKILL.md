---
trigger: security audit APK|audit Android app|APK security|find unauthenticated endpoints|Android security audit|APK pentest|mobile app audit
---

# APK Security Audit

A structured workflow for security-auditing Android applications. Downloads the APK, decompiles it, extracts all API endpoints, analyzes authentication, identifies unauthenticated endpoints, runs live PoC tests, and produces a structured report.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| [apkeep](https://github.com/nicolo-ribaudo/apkeep) | Download APKs from Google Play | `cargo install apkeep` |
| [jadx](https://github.com/skylot/jadx) | DEX → Java decompiler | `brew install jadx` |
| Java 17+ | Required by jadx | `brew install openjdk@17` |
| [uv](https://github.com/astral-sh/uv) | Python package runner for PoC scripts | `brew install uv` |

Optional: [vineflower](https://github.com/Vineflower/vineflower), [dex2jar](https://github.com/pxb1988/dex2jar) (alternative decompilers).

Check dependencies:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/skills/android-reverse-engineering/scripts/check-deps.sh
```

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

Use the bundled decompile scripts from the android-reverse-engineering submodule.

1. Check and install dependencies:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/skills/android-reverse-engineering/scripts/check-deps.sh
   ```
   If anything is missing, install it:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/skills/android-reverse-engineering/scripts/install-dep.sh <dep>
   ```

2. Decompile:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/skills/android-reverse-engineering/scripts/decompile.sh <file>
   ```

   The output goes to `<package>-decompiled/` in the current working directory.

3. After decompilation:
   - Read `AndroidManifest.xml` from the resources directory
   - List the top-level package structure under `sources/`
   - Identify the main Activity, Application class, and architecture pattern (MVP/MVVM/Clean)
   - Report SDK/library inventory

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
bash ${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/skills/android-reverse-engineering/scripts/find-api-calls.sh <output>/sources/
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

For findings from static analysis, write Python PoC scripts to confirm:

```bash
uv run --with httpx python <appname>/poc_script.py
```

Common PoC patterns:
- Anonymous login → test authenticated-only endpoints
- GraphQL introspection → map full schema → test authorization per resolver
- Compare REST vs. GraphQL auth enforcement (dual-access patterns)
- Test for IDOR, missing auth, data leakage
- Test rate limiting on sensitive endpoints

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
