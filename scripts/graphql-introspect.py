#!/usr/bin/env python3
"""GraphQL introspection scanner — dump full schema from any endpoint.

Usage:
    uv run --with httpx python graphql-introspect.py <url> [--token <token>] [--output <file>]

Tests introspection with and without auth to identify what's exposed to anonymous users.
"""
import argparse
import json
import sys

INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      kind
      name
      fields(includeDeprecated: true) {
        name
        args { name type { ...TypeRef } }
        type { ...TypeRef }
      }
      inputFields { name type { ...TypeRef } }
      enumValues(includeDeprecated: true) { name }
    }
  }
}

fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType { kind name }
    }
  }
}
"""

SIMPLE_QUERY = '{ __schema { queryType { name } mutationType { name } types { name kind } } }'


def introspect(url, token=None, headers=None):
    import httpx

    hdrs = {"Content-Type": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    if headers:
        for h in headers:
            k, v = h.split(":", 1)
            hdrs[k.strip()] = v.strip()

    # Try full introspection first
    resp = httpx.post(url, json={"query": INTROSPECTION_QUERY}, headers=hdrs, timeout=30)
    data = resp.json()

    if "errors" in data and not data.get("data", {}).get("__schema"):
        # Fall back to simple query (some servers block deep introspection)
        resp = httpx.post(url, json={"query": SIMPLE_QUERY}, headers=hdrs, timeout=30)
        data = resp.json()

    return data


def summarize(schema_data):
    schema = schema_data.get("data", {}).get("__schema", {})
    if not schema:
        return "Introspection blocked or returned no data."

    lines = []
    types = schema.get("types", [])

    # Separate user-defined types from builtins
    user_types = [t for t in types if not t["name"].startswith("__")]
    queries = []
    mutations = []

    query_type_name = (schema.get("queryType") or {}).get("name", "Query")
    mutation_type_name = (schema.get("mutationType") or {}).get("name", "Mutation")

    for t in types:
        if t["name"] == query_type_name and t.get("fields"):
            queries = t["fields"]
        if t["name"] == mutation_type_name and t.get("fields"):
            mutations = t["fields"]

    lines.append(f"Types: {len(user_types)} | Queries: {len(queries)} | Mutations: {len(mutations)}")
    lines.append("")

    if queries:
        lines.append("=== QUERIES ===")
        for q in sorted(queries, key=lambda x: x["name"]):
            args = ", ".join(a["name"] for a in q.get("args", []))
            lines.append(f"  {q['name']}({args})")

    if mutations:
        lines.append("")
        lines.append("=== MUTATIONS ===")
        for m in sorted(mutations, key=lambda x: x["name"]):
            args = ", ".join(a["name"] for a in m.get("args", []))
            lines.append(f"  {m['name']}({args})")

    # Flag suspicious operations
    suspicious = []
    for op in queries + mutations:
        name = op["name"].lower()
        if any(kw in name for kw in ["admin", "delete", "internal", "accounting",
                                      "publish", "create_user", "remove", "config",
                                      "secret", "password", "credential"]):
            suspicious.append(op["name"])

    if suspicious:
        lines.append("")
        lines.append("=== SUSPICIOUS OPERATIONS (check auth!) ===")
        for s in suspicious:
            lines.append(f"  !! {s}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="GraphQL introspection scanner")
    parser.add_argument("url", help="GraphQL endpoint URL")
    parser.add_argument("--token", help="Bearer token for authenticated introspection")
    parser.add_argument("--header", "-H", action="append", help="Extra header (Key: Value)")
    parser.add_argument("--output", "-o", help="Save full schema JSON to file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only print summary")
    args = parser.parse_args()

    print(f"[*] Introspecting {args.url}")
    if args.token:
        print(f"[*] Using auth token: {args.token[:20]}...")
    else:
        print("[*] No auth token — testing anonymous access")

    try:
        result = introspect(args.url, token=args.token, headers=args.header)
    except Exception as e:
        print(f"[!] Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    if "errors" in result:
        print(f"[!] Errors: {json.dumps(result['errors'], indent=2)}")

    schema = result.get("data", {}).get("__schema")
    if schema:
        print("[+] Introspection ENABLED")
        print()
        print(summarize(result))
    else:
        print("[-] Introspection blocked or no schema returned")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n[*] Full schema saved to {args.output}")
    elif not args.quiet:
        print(f"\n[*] Tip: re-run with --output schema.json to save full schema")


if __name__ == "__main__":
    main()
