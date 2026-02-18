#!/usr/bin/env python3
"""Extract string literals from Hermes bytecode bundles.

Usage:
    uv run python extract-strings-hermes.py <bundle.hbc> [--filter-urls] [--filter-api] [--output <file>]

Hermes-compiled React Native bundles are bytecode, not readable JS.
This script extracts all string literals from the string table,
which contains URLs, API paths, auth headers, config keys, and more.
"""
import argparse
import json
import re
import struct
import sys


def read_hermes_strings(filepath):
    """Extract strings from a Hermes bytecode file's string table."""
    with open(filepath, "rb") as f:
        magic = f.read(8)

        # Check for Hermes magic bytes
        if magic[:4] != b'\xc6\x1f\xbc\x03' and b'Hermes' not in magic:
            # Try reading as raw binary and extracting printable strings
            f.seek(0)
            data = f.read()
            return extract_printable_strings(data)

        # Read the full file
        f.seek(0)
        data = f.read()

    return extract_printable_strings(data)


def extract_printable_strings(data, min_length=4):
    """Extract all printable ASCII strings from binary data."""
    strings = []
    pattern = re.compile(rb'[\x20-\x7e]{%d,}' % min_length)
    for match in pattern.finditer(data):
        try:
            s = match.group().decode('ascii')
            strings.append(s)
        except UnicodeDecodeError:
            continue
    return strings


def filter_urls(strings):
    """Filter strings that look like URLs."""
    url_pattern = re.compile(r'https?://[a-zA-Z0-9._\-/:%@?&=#+]+')
    results = []
    for s in strings:
        matches = url_pattern.findall(s)
        results.extend(matches)
    return sorted(set(results))


def filter_api_paths(strings):
    """Filter strings that look like API paths."""
    path_pattern = re.compile(r'^/[a-zA-Z0-9_\-/{}:.]+$')
    keywords = ['api', 'auth', 'login', 'token', 'user', 'graphql', 'query',
                'mutation', 'v1', 'v2', 'v3', 'oauth', 'callback', 'webhook']
    results = []
    for s in strings:
        if path_pattern.match(s):
            results.append(s)
        elif any(kw in s.lower() for kw in keywords) and '/' in s and len(s) < 200:
            results.append(s)
    return sorted(set(results))


def filter_secrets(strings):
    """Filter strings that might be secrets or keys."""
    secret_patterns = [
        re.compile(r'[A-Za-z0-9_]*(api[_-]?key|secret|token|password|credential)[A-Za-z0-9_]*', re.I),
        re.compile(r'^AIza[0-9A-Za-z_-]{35}$'),  # Google API key
        re.compile(r'^[A-Za-z0-9+/]{40,}={0,2}$'),  # Base64 encoded (long)
        re.compile(r'Bearer\s+\S+', re.I),
        re.compile(r'Authorization', re.I),
    ]
    results = []
    for s in strings:
        for p in secret_patterns:
            if p.search(s):
                results.append(s)
                break
    return sorted(set(results))


def main():
    parser = argparse.ArgumentParser(description="Extract strings from Hermes bytecode")
    parser.add_argument("file", help="Path to Hermes bytecode bundle (.hbc or index.android.bundle)")
    parser.add_argument("--filter-urls", action="store_true", help="Show only URLs")
    parser.add_argument("--filter-api", action="store_true", help="Show only API paths")
    parser.add_argument("--filter-secrets", action="store_true", help="Show potential secrets/keys")
    parser.add_argument("--min-length", type=int, default=4, help="Minimum string length (default: 4)")
    parser.add_argument("--output", "-o", help="Save results to file")
    args = parser.parse_args()

    print(f"[*] Extracting strings from {args.file}")

    strings = read_hermes_strings(args.file)
    print(f"[*] Found {len(strings)} strings (min length {args.min_length})")

    # Apply filters
    if args.filter_urls:
        strings = filter_urls(strings)
        print(f"[*] URLs found: {len(strings)}")
    elif args.filter_api:
        strings = filter_api_paths(strings)
        print(f"[*] API paths found: {len(strings)}")
    elif args.filter_secrets:
        strings = filter_secrets(strings)
        print(f"[*] Potential secrets found: {len(strings)}")

    output_lines = []
    for s in strings:
        output_lines.append(s)
        if not args.output:
            print(s)

    if args.output:
        with open(args.output, "w") as f:
            f.write("\n".join(output_lines))
        print(f"[*] Saved {len(output_lines)} strings to {args.output}")

    # Always print a summary of interesting findings
    if not args.filter_urls and not args.filter_api and not args.filter_secrets:
        urls = filter_urls(strings)
        apis = filter_api_paths(strings)
        secrets = filter_secrets(strings)
        print(f"\n--- Summary ---")
        print(f"URLs:            {len(urls)}")
        print(f"API paths:       {len(apis)}")
        print(f"Potential secrets:{len(secrets)}")
        print(f"\nRe-run with --filter-urls, --filter-api, or --filter-secrets for details.")


if __name__ == "__main__":
    main()
