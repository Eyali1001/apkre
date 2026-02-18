<p align="center">
  <img src="logo.png" alt="apk-audit" width="200">
</p>

<h1 align="center">apk-audit</h1>

<p align="center">
  <strong>One command. Full Android security audit.</strong><br>
  A <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a> plugin that tears apart APKs so you don't have to.
</p>

<p align="center">
  <a href="#installation"><img src="https://img.shields.io/badge/Claude_Code-plugin-blueviolet?style=for-the-badge" alt="Claude Code Plugin"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="MIT License"></a>
</p>

---

```
/apk-audit that israeli parking app
```

That's it. Claude finds the app on Google Play, downloads the APK, decompiles it, maps every API endpoint, traces the auth flow, identifies what's callable without a token, writes PoC scripts to prove it, and hands you a structured security report.

---

## How it works

| Phase | What happens |
|:------|:-------------|
| **0. Resolve** | Describe the app in plain English — Claude searches Google Play and finds the package name |
| **1. Download** | Fetches the APK via [apkeep](https://github.com/nicolo-ribaudo/apkeep) |
| **2. Decompile** | Runs [jadx](https://github.com/skylot/jadx) via the [android-reverse-engineering-skill](https://github.com/SimoneAvogadro/android-reverse-engineering-skill) (bundled as submodule) |
| **3. Analyze** | Parallel agents extract API endpoints, auth mechanisms, SSL pinning, third-party SDKs |
| **4. Unauth scan** | Identifies endpoints callable without authentication — the money shot |
| **5. Live test** | Generates and runs Python PoC scripts to confirm findings |
| **6. Report** | Produces a severity-rated markdown report |

## Quick start

### Prerequisites

```bash
cargo install apkeep          # APK downloader
brew install jadx              # Decompiler
brew install openjdk@17        # Java runtime
brew install uv                # Python runner for PoCs
```

### Install the plugin

**Marketplace:**
```
/plugin marketplace add Eyali1001/apkre
```

**Manual:**
```bash
git clone --recurse-submodules git@github.com:Eyali1001/apkre.git
```
```
/plugin add /path/to/apkre
```

## Usage

Pass anything — a description, a package name, or a file path:

```bash
/apk-audit that food delivery app everyone uses in Israel

/apk-audit com.example.app

/apk-audit ./downloads/com.example.app.xapk
```

## What you get

```
./
├── myapp/
│   ├── com.example.app.xapk       # Downloaded APK
│   ├── myapp_report.md             # Security audit report
│   ├── anon_probe.py               # PoC: unauthenticated endpoint tests
│   ├── anon_login.py               # PoC: anonymous session creation
│   └── ...
└── com.example.app-decompiled/     # Full decompiled source
    └── com.example.app/
        ├── resources/
        │   └── AndroidManifest.xml
        └── sources/                # Java/Kotlin source
```

The report includes: app metadata, full endpoint map, unauthenticated endpoints with risk ratings, auth flow analysis, SSL pinning status, third-party SDK inventory, live test results, and prioritized recommendations.

## Handles the hard stuff

- **Obfuscated code** — Knows R8/ProGuard annotation mappings, uses string literals as anchors
- **React Native / Hermes** — Extracts strings from Hermes bytecode bundles
- **Hybrid apps** — Searches Capacitor/Cordova JS bundles alongside native code
- **GraphQL** — Tests introspection, maps schemas, checks per-resolver auth
- **Split APKs** — Handles XAPK bundles with multiple split APKs

## License

MIT
