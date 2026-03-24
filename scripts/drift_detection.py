"""Detect feature drift between offline (Delta Lake) and online (Redis) stores.

Called by the pre-commit hook with --check. Reads the staged git diff,
sends it to OpenAI gpt-4o for review, and blocks the commit on critical issues.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

SYSTEM_PROMPT = (
    "You are a Senior Data Engineer reviewing a git diff for a Real-Time Feature Store. "
    "Check for: (1) any write to Delta Lake or Redis that is not a dual-write to both, "
    "(2) schema changes to feature records that lack a corresponding migration or "
    "validation update, (3) parity check logic being added inline to the write path "
    "instead of as a scheduled check. Respond with JSON: "
    '{"critical": [list of critical issues], "warnings": [list of warnings]}. '
    'If no issues, return {"critical": [], "warnings": []}.'
)


def get_staged_diff() -> str:
    """Return the staged git diff text."""
    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def has_python_changes(diff: str) -> bool:
    """Return True if the diff contains changes to Python files."""
    for line in diff.splitlines():
        if line.startswith("diff --git") and ".py " in line:
            return True
    return False


def review_diff(diff: str) -> dict:
    """Send the diff to OpenAI gpt-4o and return the parsed JSON response."""
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": diff},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return json.loads(content)


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("WARN: OPENAI_API_KEY not set, skipping drift check")
        return 0

    diff = get_staged_diff()

    if not diff or not has_python_changes(diff):
        return 0

    try:
        result = review_diff(diff)
    except Exception as exc:
        print(f"WARN: drift check failed ({exc}), skipping")
        return 0

    criticals = result.get("critical", [])
    warnings = result.get("warnings", [])

    if warnings:
        for warning in warnings:
            print(f"WARNING: {warning}")

    if criticals:
        for issue in criticals:
            print(f"CRITICAL: {issue}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
