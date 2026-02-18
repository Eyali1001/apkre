#!/usr/bin/env python3
"""Test endpoints with and without authentication.

Usage:
    uv run --with httpx python test-unauth.py --base-url <url> --endpoints endpoints.json [--token <token>]

endpoints.json format:
[
  {"method": "GET",  "path": "/api/v1/users/me"},
  {"method": "POST", "path": "/api/v1/search", "body": {"query": "test"}},
  {"method": "POST", "path": "/graphql", "body": {"query": "{ viewer { id } }"}}
]

Or simply a list of paths (defaults to GET):
["/api/v1/users/me", "/api/v1/config", "/api/v1/health"]
"""
import argparse
import json
import sys
import time


def classify_response(resp):
    """Classify a response as BLOCKED, ERROR, or DATA_RETURNED."""
    if resp.status_code in (401, 403):
        return "BLOCKED"
    if resp.status_code == 404:
        return "NOT_FOUND"
    if resp.status_code >= 500:
        return "SERVER_ERROR"
    if resp.status_code == 429:
        return "RATE_LIMITED"

    try:
        body = resp.json()
    except Exception:
        if resp.status_code == 200:
            return "DATA_RETURNED"
        return "ERROR"

    # GraphQL-style errors
    if "errors" in body:
        errors = body["errors"]
        for e in errors:
            msg = str(e.get("message", "")).lower()
            code = str(e.get("extensions", {}).get("code", "")).lower()
            if any(kw in msg or kw in code for kw in ["unauthorized", "forbidden", "auth", "permission", "login"]):
                return "BLOCKED"
        if body.get("data"):
            return "DATA_RETURNED"
        return "ERROR"

    if body and resp.status_code == 200:
        return "DATA_RETURNED"

    return "ERROR"


def test_endpoint(client, base_url, endpoint, token=None, extra_headers=None):
    """Test a single endpoint with optional auth."""
    import httpx

    if isinstance(endpoint, str):
        endpoint = {"method": "GET", "path": endpoint}

    method = endpoint.get("method", "GET").upper()
    path = endpoint["path"]
    body = endpoint.get("body")
    url = f"{base_url.rstrip('/')}{path}"

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)

    try:
        if method == "GET":
            resp = client.get(url, headers=headers, timeout=15)
        elif method == "POST":
            resp = client.post(url, json=body or {}, headers=headers, timeout=15)
        elif method == "PUT":
            resp = client.put(url, json=body or {}, headers=headers, timeout=15)
        elif method == "DELETE":
            resp = client.delete(url, headers=headers, timeout=15)
        else:
            resp = client.request(method, url, json=body, headers=headers, timeout=15)

        classification = classify_response(resp)
        return {
            "status": resp.status_code,
            "classification": classification,
            "body_preview": str(resp.text)[:200],
        }
    except Exception as e:
        return {
            "status": None,
            "classification": "CONN_ERROR",
            "body_preview": str(e),
        }


def main():
    import httpx

    parser = argparse.ArgumentParser(description="Test endpoints with/without auth")
    parser.add_argument("--base-url", required=True, help="API base URL")
    parser.add_argument("--endpoints", required=True, help="JSON file with endpoint list")
    parser.add_argument("--token", help="Bearer token for authenticated testing")
    parser.add_argument("--header", "-H", action="append", help="Extra header (Key: Value)")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between requests (seconds)")
    parser.add_argument("--output", "-o", help="Save results to JSON file")
    args = parser.parse_args()

    with open(args.endpoints) as f:
        endpoints = json.load(f)

    extra_headers = {}
    if args.header:
        for h in args.header:
            k, v = h.split(":", 1)
            extra_headers[k.strip()] = v.strip()

    results = []
    client = httpx.Client()

    print(f"Testing {len(endpoints)} endpoints against {args.base_url}")
    print(f"{'METHOD':<7} {'PATH':<50} {'ANON':<15} {'AUTH':<15}")
    print("-" * 90)

    for ep in endpoints:
        path = ep["path"] if isinstance(ep, dict) else ep

        # Test without auth
        anon_result = test_endpoint(client, args.base_url, ep, token=None, extra_headers=extra_headers)
        time.sleep(args.delay)

        # Test with auth (if token provided)
        auth_result = None
        if args.token:
            auth_result = test_endpoint(client, args.base_url, ep, token=args.token, extra_headers=extra_headers)
            time.sleep(args.delay)

        method = ep.get("method", "GET") if isinstance(ep, dict) else "GET"
        anon_class = anon_result["classification"]
        auth_class = auth_result["classification"] if auth_result else "—"

        # Highlight dangerous: anon returns data
        marker = " !!" if anon_class == "DATA_RETURNED" else ""
        print(f"{method:<7} {path:<50} {anon_class:<15} {auth_class:<15}{marker}")

        results.append({
            "method": method,
            "path": path,
            "anon": anon_result,
            "auth": auth_result,
        })

    # Summary
    anon_data = sum(1 for r in results if r["anon"]["classification"] == "DATA_RETURNED")
    anon_blocked = sum(1 for r in results if r["anon"]["classification"] == "BLOCKED")
    print(f"\n{'='*90}")
    print(f"ANON DATA_RETURNED: {anon_data}/{len(results)}  |  ANON BLOCKED: {anon_blocked}/{len(results)}")

    if anon_data > 0:
        print(f"\n[!!] {anon_data} endpoint(s) return data WITHOUT authentication:")
        for r in results:
            if r["anon"]["classification"] == "DATA_RETURNED":
                print(f"     {r['method']} {r['path']}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n[*] Full results saved to {args.output}")

    client.close()


if __name__ == "__main__":
    main()
