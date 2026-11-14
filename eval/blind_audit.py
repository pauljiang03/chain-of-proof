"""Did the blind builders and transcribers stay blind?

    python3 -I eval/blind_audit.py <dir with agent-<id>.jsonl session logs> <role>=<id> ...

Roles: `builder` wrote record readers and must never have touched the answer key, the
reference, the README, earlier results or the web. `transcriber` wrote reference rows
and must never have touched the readers or their output. This scans every tool call an
agent made (the call's input only, never its output) for a path or tool that breaks its
rule, and prints each hit. An empty list is the evidence that the closed-book numbers
were produced closed-book.
"""
import json
import re
import sys
from pathlib import Path

FORBIDDEN = {
    "builder": [r"leakage-answers", r"answers\.txt", r"\beval/", r"reference_parts", r"blind/reference",
                r"README\.md", r"TASKS\.md", r"chain-of-proof\S*\.md", r"\bruns/", r"\bcerts/",
                r"labeled_claims", r"cfreds", r"mulder"],
    "transcriber": [r"\bextractor/", r"case_facts", r"\bevidence/", r"blind/(system|webcloud|files|media)",
                    r"\bruns/", r"\bcerts/", r"\.E01", r"mulder"],
}
# Allowed, but worth knowing: a builder that read the evidence file our earlier readers
# produced (values taken from the images, not from the answer key).
NOTED = {"builder": [r"case_facts"], "transcriber": []}
WEB_TOOLS = ("WebSearch", "WebFetch")


def calls(path: Path):
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message") or {}
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block.get("name", ""), json.dumps(block.get("input", {}), ensure_ascii=False)


def audit(path: Path, role: str):
    total, hits, noted = 0, [], 0
    for name, text in calls(path):
        if name == "SubagentHandback":
            continue                    # the agent's closing report, not an access
        total += 1
        if name in WEB_TOOLS or name == "Agent":
            hits.append((name, "tool not allowed for this role", text[:160]))
            continue
        noted += any(re.search(p, text, re.I) for p in NOTED[role])
        for pattern in FORBIDDEN[role]:
            m = re.search(pattern, text, re.I)
            if m:
                lo = max(0, m.start() - 70)
                hits.append((name, pattern, text[lo:m.end() + 70].replace("\\n", " ")))
                break
    return total, hits, noted


def main(argv) -> int:
    logs, bad = Path(argv[0]), 0
    for spec in argv[1:]:
        role, agent = spec.split("=")
        total, hits, noted = audit(logs / f"agent-{agent}.jsonl", role)
        print(f"{role:<12}{agent}  {total} tool calls, {len(hits)} to check"
              + (f"; {noted} read our earlier evidence file (allowed)" if noted else ""))
        for name, why, snippet in hits:
            print(f"    {name} [{why}] …{snippet}…")
        bad += len(hits)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
