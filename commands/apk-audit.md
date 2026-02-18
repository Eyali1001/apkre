---
allowed-tools: Bash, Read, Glob, Grep, Write, Edit, WebFetch, WebSearch, Task
description: Security-audit an Android APK — download, decompile, analyze APIs & auth, test unauthenticated endpoints, generate report
user-invocable: true
argument: Google Play package name (e.g. com.example.app) or path to APK/XAPK file
---

# /apk-audit

Run a full security audit on an Android application.

## Instructions

You are starting the APK security audit workflow. Follow the full playbook defined in `${CLAUDE_PLUGIN_ROOT}/skills/apk-audit/SKILL.md`.

### Determine the target

If the user provided an argument:
- If it looks like a **file path** (contains `/` or ends in `.apk`/`.xapk`), use it directly as the target file and skip to Phase 2.
- If it looks like a **package name** (e.g. `com.example.app`), proceed with Phase 1 to download it.

If no argument was provided, ask the user for either a package name or file path.

### Run the audit

Follow Phases 1–6 from the skill playbook. Use parallel agents where the playbook recommends it (Phase 3 especially).

### Decompilation

For the decompile step (Phase 2), use the bundled decompile scripts from the submodule:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/skills/android-reverse-engineering/scripts/check-deps.sh
bash ${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/skills/android-reverse-engineering/scripts/decompile.sh <file>
```

### Output

Save the final report to `<appname>/<appname>_report.md` using the template in `${CLAUDE_PLUGIN_ROOT}/skills/apk-audit/templates/report-template.md`.
