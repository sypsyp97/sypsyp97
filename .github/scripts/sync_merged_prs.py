"""Add newly merged pull requests in other projects to the profile README.

The script searches for public pull requests by the profile owner that were
merged on or after SINCE. It skips pull requests in the owner's own
repositories and in the excluded organizations, pull requests that the README
already links, repositories that the README links as a group, and pull
requests that change only documentation files. It inserts each new entry at
the top of the section, newest first.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

OWNER = "sypsyp97"
EXCLUDED_OWNERS = {OWNER, "NX-AI"}
SINCE = "2026-11-13"
HEADING = "## 🤝 Selected merged pull requests in other projects"
README = Path("README.md")

CONVENTIONAL_PREFIX = re.compile(r"^[a-z]+(\([^)]*\))?!?:\s*")
DOCS_FILE = re.compile(
    r"(^|/)(docs?|documentation)/"
    r"|\.(md|mdx|rst)$"
    r"|(^|/)(LICENSE|COPYING|README|CHANGELOG|AUTHORS|CONTRIBUTING)"
    r"(-[^/.]*)?(\.txt)?$",
    re.IGNORECASE,
)


def merged_prs():
    out = subprocess.run(
        [
            "gh", "search", "prs",
            "--author", OWNER,
            "--merged",
            "--visibility", "public",
            "--merged-at", f">={SINCE}",
            "--limit", "100",
            "--json", "url,title,number,repository,closedAt",
        ],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)


def docs_only(repo, number):
    out = subprocess.run(
        [
            "gh", "api", "--paginate",
            f"repos/{repo}/pulls/{number}/files",
            "--jq", ".[].filename",
        ],
        check=True, capture_output=True, text=True,
    ).stdout
    return all(DOCS_FILE.search(name) for name in out.splitlines())


def entry_text(title):
    text = CONVENTIONAL_PREFIX.sub("", title.strip()).rstrip(".")
    return text[:1].upper() + text[1:] + "."


def main():
    lines = README.read_text().splitlines(keepends=True)
    start = lines.index(HEADING + "\n")
    first_item = start + 1
    while not lines[first_item].startswith("- "):
        first_item += 1
    section_end = first_item
    while section_end < len(lines) and lines[section_end].startswith("- "):
        section_end += 1
    section = "".join(lines[first_item:section_end])

    new = []
    for pr in sorted(merged_prs(), key=lambda p: p["closedAt"], reverse=True):
        repo = pr["repository"]["nameWithOwner"]
        owner = repo.split("/")[0]
        if owner in EXCLUDED_OWNERS:
            continue
        if pr["url"] in section or f"https://github.com/{repo}/pulls?" in section:
            continue
        if docs_only(repo, pr["number"]):
            continue
        new.append(
            f"- **[{repo} #{pr['number']}]({pr['url']})**: {entry_text(pr['title'])}\n"
        )

    if not new:
        print("No new merged pull requests.")
        return 0
    lines[first_item:first_item] = new
    README.write_text("".join(lines))
    print("".join(new), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
