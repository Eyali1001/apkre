# apk-audit

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin for security-auditing Android applications.

Run `/apk-audit com.example.app` and Claude will download the APK, decompile it, extract all API endpoints, analyze authentication, identify unauthenticated endpoints, run live PoC tests, and generate a structured security report.

## What it does

1. **Download** — Fetches the APK from Google Play via [apkeep](https://github.com/nicolo-ribaudo/apkeep)
2. **Decompile** — Decompiles with [jadx](https://github.com/skylot/jadx) (delegates to [android-reverse-engineering-skill](https://github.com/SimoneAvogadro/android-reverse-engineering-skill))
3. **Analyze** — Extracts API endpoints, auth flows, SSL pinning, third-party SDKs
4. **Find unauthenticated endpoints** — Identifies endpoints callable without auth tokens
5. **Live test** — Generates and runs Python PoC scripts to confirm findings
6. **Report** — Produces a structured markdown report with severity ratings

## Prerequisites

Install these before using the plugin:

```bash
# Required
cargo install apkeep          # APK downloader
brew install jadx              # Decompiler
brew install openjdk@17        # Java runtime for jadx
brew install uv                # Python runner for PoC scripts

# Optional (better decompilation)
# brew install vineflower
# brew install dex2jar
```

## Installation

### From the Claude Code plugin marketplace

```
/plugin marketplace add Eyali1001/apkre
```

### Manual installation

```bash
# Clone with submodules
git clone --recurse-submodules git@github.com:Eyali1001/apkre.git

# Or if already cloned without submodules:
git submodule update --init --recursive
```

Then add the plugin to Claude Code:

```
/plugin add /path/to/apk-audit
```

## Usage

```
/apk-audit com.example.app
```

Or with an existing APK file:

```
/apk-audit ./myapp/com.example.app.xapk
```

The audit produces:
- Decompiled source in `<package>-decompiled/`
- PoC scripts in `<appname>/`
- Final report at `<appname>/<appname>_report.md`

## Output structure

```
./
├── <appname>/
│   ├── <package>.xapk           # Downloaded APK
│   ├── <appname>_report.md      # Security audit report
│   ├── anon_login.py            # PoC scripts
│   └── ...
└── <package>-decompiled/        # Decompiled source (jadx output)
    └── <package>/
        ├── resources/
        │   └── AndroidManifest.xml
        └── sources/
```

## License

MIT
