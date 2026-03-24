"""Pre-commit safety review — calls OpenAI to flag unsafe model promotions."""

import argparse
import subprocess
import sys


def get_staged_diff() -> str:
    """Read the staged git diff."""
    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True,
        text=True,
    )
    return result.stdout


def review_diff(diff: str) -> None:
    """Send diff to OpenAI gpt-4o for safety review."""
    import openai

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a Senior MLOps Engineer performing a pre-commit safety review. "
                    "Flag CRITICAL if you find: unsafe model promotion logic, missing rollback "
                    "conditions, or undefined SLOs. Respond ONLY with PASS or CRITICAL: <reason>."
                ),
            },
            {"role": "user", "content": diff},
        ],
    )
    verdict = response.choices[0].message.content.strip()
    if verdict.startswith("CRITICAL"):
        print(verdict)
        sys.exit(1)
    print("PASS")
    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    diff = get_staged_diff()

    if args.dry_run:
        print(f"[dry-run] Staged diff length: {len(diff)} chars. Skipping API call.")
        sys.exit(0)

    if not diff:
        print("No staged changes. Skipping review.")
        sys.exit(0)

    review_diff(diff)


if __name__ == "__main__":
    main()
