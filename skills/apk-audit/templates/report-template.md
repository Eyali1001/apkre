# {{APP_NAME}} — Security Audit Report

## App Info

| Field | Value |
|-------|-------|
| Package | `{{PACKAGE_NAME}}` |
| Version | {{VERSION}} |
| Min SDK | {{MIN_SDK}} |
| Target SDK | {{TARGET_SDK}} |
| Architecture | {{ARCHITECTURE}} (Native / React Native / Flutter / Capacitor) |

## API Endpoints

| Method | Path | Base URL | Auth Required | Notes |
|--------|------|----------|---------------|-------|
| GET | /example | https://api.example.com | Yes | — |

## Unauthenticated Endpoints

| Method | Path | Risk | Data Exposed | Rate Limited |
|--------|------|------|--------------|--------------|
| GET | /example | HIGH | User PII | No |

## Authentication System

- **Login mechanism**: (password / OTP / biometric / OAuth / etc.)
- **Token type**: (JWT / session cookie / custom header)
- **Token storage**: (SharedPreferences / AsyncStorage / Keychain)
- **Token refresh**: (how tokens are refreshed, expiry handling)
- **Auth interceptor**: (global OkHttp/axios interceptor details)

## SSL Pinning

- **Implementation**: (CertificatePinner / TrustManager / none)
- **Pinned domains**: (list of domains and certificate hashes, or "not implemented")

## Third-Party Services

| Service | URL / SDK | Exposed Keys |
|---------|-----------|--------------|
| Firebase | — | — |

## Storage

- **Token storage**: (where auth tokens are persisted)
- **Local databases**: (Room / SQLite / Realm)
- **SharedPreferences**: (sensitive data in plaintext?)

## Live Endpoint Testing

| Endpoint | Test | Result | Notes |
|----------|------|--------|-------|
| GET /example | Anonymous request | 200 OK — returned data | No auth check |

## Security Observations

| # | Severity | Finding |
|---|----------|---------|
| 1 | CRITICAL | — |
| 2 | HIGH | — |
| 3 | MEDIUM | — |
| 4 | LOW | — |
| 5 | INFO | — |

## Recommendations

1. (Prioritized remediation steps)
