---
allowed-tools: Bash, Read, Glob, Grep, Write, Edit, WebFetch, WebSearch, Task
description: Security-audit an Android APK — download, decompile, analyze APIs & auth, test unauthenticated endpoints, generate report
user-invocable: true
argument: app description, Google Play package name, or path to APK/XAPK file
---

# /apk-audit

Run a full security audit on an Android application.

## Instructions

You are starting the APK security audit workflow. Follow the full playbook defined in `${CLAUDE_PLUGIN_ROOT}/skills/apk-audit/SKILL.md`.

### Determine the target

The user's argument can be one of three things:

1. **File path** (contains `/` or ends in `.apk`/`.xapk`) → use it directly, skip to Phase 2.
2. **Package name** (matches `com.x.y` / `org.x.y` pattern) → proceed to Phase 1 download.
3. **App description** (anything else — e.g. "the israeli parking app", "Domino's Pizza Israel") → resolve it to a package name first using Phase 0.

If no argument was provided, ask the user what app they want to audit.

### Phase 0: Resolve app description to package name

When the input is a natural-language description (not a file path or package name):

1. **Search the web** for the app on Google Play:
   ```
   WebSearch: "<description>" site:play.google.com
   ```
2. From the search results, find the Google Play URL. The package name is in the `id=` parameter:
   `https://play.google.com/store/apps/details?id=com.example.app` → `com.example.app`
3. If multiple results match, pick the most relevant one and **confirm with the user** before proceeding:
   > "I found **App Name** (`com.example.app`) on Google Play. Is this the app you want to audit?"
4. Once confirmed, proceed to Phase 1 with the resolved package name.

### Run the audit

Follow Phases 1–6 from the skill playbook. Use parallel agents where the playbook recommends it (Phase 3 especially).

### Dependencies

Before anything else, check and auto-install dependencies:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check-deps.sh
```

If anything is missing, install it:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/install-dep.sh <dep>
```

### Decompilation

For Phase 2, read and follow the full android-reverse-engineering skill at `${CLAUDE_PLUGIN_ROOT}/android-reverse-engineering-skill/plugins/android-reverse-engineering/skills/android-reverse-engineering/SKILL.md`. It contains guidance on engine selection, structure analysis, call flow tracing, and obfuscated code handling that goes beyond just running the decompile script.

### Output

Save the final report to `<appname>/<appname>_report.md` using the template in `${CLAUDE_PLUGIN_ROOT}/skills/apk-audit/templates/report-template.md`.
