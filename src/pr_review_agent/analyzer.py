from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Union


KNOWN_LIBRARIES = {
    "fastapi": "backend",
    "django": "backend",
    "flask": "backend",
    "pandas": "data",
    "numpy": "data",
    "sqlalchemy": "database",
    "psycopg": "database",
    "pytest": "testing",
    "requests": "network",
    "boto3": "cloud",
    "celery": "backend",
    "redis": "backend",
    "tensorflow": "ml",
    "torch": "ml",
    "transformers": "ml",
    "playwright": "ui",
    "selenium": "ui",
    "react": "ui",
    "next": "ui",
    "vue": "ui",
    "pydantic": "backend",
    "openai": "ai",
    "anthropic": "ai",
    "ollama": "ai",
    "click": "tooling",
    "typer": "tooling",
    "gunicorn": "backend",
    "uvicorn": "backend",
}

SECURITY_PATTERNS = {
    "subprocess": "Potential command execution in app code",
    "eval(": "Dynamic evaluation of code strings",
    "pickle.loads": "Unsafe deserialization risk",
    "yaml.load": "Unsafe YAML deserialization",
    "os.system": "Shell command execution risk",
    "exec(": "Dynamic code execution risk",
    "requests.get": "Remote network call may need review",
    "password": "Potential secret handling or credential references",
    "SECRET": "High-risk secret-like variable naming",
    "api_key": "Possible API key handling",
    "token": "Potential token handling",
}


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _get_changed_files(repo: Path, base_ref: str) -> list[str]:
    diff = _run_git(repo, "diff", "--name-only", f"{base_ref}...HEAD")
    if not diff:
        diff = _run_git(repo, "diff", "--name-only", base_ref)
    return [line.strip() for line in diff.splitlines() if line.strip()]


def _read_file(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _classify_review_area(file_path: str) -> str:
    lower = file_path.lower()
    if lower.endswith((".ts", ".tsx", ".js", ".jsx", ".css", ".html")) or "/ui/" in lower or "frontend" in lower:
        return "ui"
    if lower.endswith((".sql", ".db", ".ddl")) or "/migrations/" in lower or "db" in lower:
        return "database"
    if "/.github/" in lower or lower.endswith((".yml", ".yaml")) or "pipeline" in lower or "workflows" in lower:
        return "pipeline"
    if lower.endswith((".py", ".go", ".java", ".rs", ".js", ".ts")):
        return "backend"
    return "general"


def _extract_dependency_names(files: list[str], repo: Path) -> list[str]:
    deps: set[str] = set()
    for file_name in files:
        path = repo / file_name
        if not path.exists():
            continue
        content = _read_file(path)
        for name in KNOWN_LIBRARIES:
            if re.search(rf"(?i)\b{name}\b|\b{name}\s*[=<>!~]", content):
                deps.add(name)
        if "requirements.txt" in file_name.lower() or "pyproject.toml" in file_name.lower() or "package.json" in file_name.lower():
            for line in content.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" in stripped:
                    dep = stripped.split("=")[0].strip()
                    deps.add(dep)
                elif ">" in stripped or "<" in stripped or "~" in stripped:
                    dep = re.split(r"[<>=!~]", stripped, 1)[0].strip()
                    deps.add(dep)
                else:
                    deps.add(stripped)
    return sorted(deps)


def _summarize_commits(repo: Path, base_ref: str) -> str:
    try:
        log = _run_git(repo, "log", "--pretty=format:%s%n%b%n---END---", f"{base_ref}..HEAD")
    except subprocess.CalledProcessError:
        log = _run_git(repo, "log", "--pretty=format:%s%n%b%n---END---", "-n", "10")
    messages = []
    for chunk in log.split("---END---"):
        text = chunk.strip()
        if text:
            messages.append(text)
    if not messages:
        return "This PR introduces a focused set of changes on the current branch."
    return " ".join(messages[:3])


def _security_scan(repo: Path, files: list[str]) -> dict[str, Any]:
    raw_signals: list[str] = []
    details: list[str] = []
    for file_name in files:
        path = repo / file_name
        if not path.exists():
            continue
        content = _read_file(path)
        for pattern, reason in SECURITY_PATTERNS.items():
            if pattern in content:
                raw_signals.append(pattern)
                details.append(f"{file_name}: {reason} ({pattern})")
    unique_signals = sorted(set(raw_signals))[:10]
    return {
        "risk_signals": unique_signals,
        "details": sorted(set(details))[:10],
        "scan_status": "warning" if unique_signals else "clean",
        "summary": "No major red flags detected." if not unique_signals else "Potential risky patterns require human review.",
    }


def _podcast_script(summary: str, security_summary: str, review_areas: list[str], important_libraries: list[str]) -> str:
    area_text = ", ".join(review_areas) if review_areas else "general maintenance"
    lib_text = ", ".join(important_libraries[:3]) if important_libraries else "no major dependency shifts"
    return (
        f"Host: This PR is focused on {area_text}, with the main story being {summary[:110]}. "
        f"The change set introduces {lib_text}. Security-wise, {security_summary.lower()} "
        f"The short take: review the behavior, confirm dependency intent, and check the key integration points before merging."
    )


def analyze_pr(repo: Union[Path, str], base_ref: str = "main", use_llm: bool = False) -> dict[str, Any]:
    repo_path = Path(repo)
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository not found: {repo_path}")

    # Guarantee a valid git repo before trying to inspect.
    try:
        _run_git(repo_path, "rev-parse", "--is-inside-work-tree")
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"Not a git repository: {repo_path}") from exc

    changed_files = _get_changed_files(repo_path, base_ref)
    if not changed_files:
        changed_files = [p.as_posix() for p in repo_path.rglob("*") if p.is_file() and ".git" not in p.parts][:20]

    important_libraries = _extract_dependency_names(changed_files, repo_path)
    review_areas = sorted({ _classify_review_area(file_name) for file_name in changed_files })
    commit_summary = _summarize_commits(repo_path, base_ref)
    security = _security_scan(repo_path, changed_files)

    summary_text = (
        f"This PR updates {len(changed_files)} files and focuses on {', '.join(review_areas) if review_areas else 'general maintenance'}. "
        f"The change set appears to be about {commit_summary[:180]}."
    )

    result = {
        "summary": summary_text,
        "base_ref": base_ref,
        "changed_files": changed_files,
        "review_areas": review_areas,
        "important_libraries": important_libraries,
        "security": security,
        "podcast": _podcast_script(commit_summary, security["summary"], review_areas, important_libraries),
        "llm_enabled": use_llm,
    }

    if use_llm:
        result["llm_note"] = "Local LLM enhancement is enabled, but no remote model is required for the default analysis."

    return result


def build_pr_report(result: dict[str, Any]) -> str:
    libraries = result["important_libraries"] or ["no major dependency changes detected"]
    risk_signals = result["security"]["risk_signals"] or ["none"]
    review_areas = result["review_areas"] or ["general"]
    report = [
        "# PR Review Snapshot",
        "",
        "## Storyline",
        result["summary"],
        "",
        "## Focus areas",
        "- " + "\n- ".join(review_areas),
        "",
        "## Dependencies",
        "- " + "\n- ".join(libraries),
        "",
        "## Security",
        f"- Status: {result['security']['scan_status']}",
        f"- Signals: {', '.join(risk_signals)}",
        "",
        "## Podcast note",
        result["podcast"],
    ]
    return "\n".join(report)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Summarize a pull request from a local git repository.")
    parser.add_argument("--repo", required=True, help="Path to the local git repo")
    parser.add_argument("--base", default="main", help="Base branch to compare against")
    parser.add_argument("--output", default="pr_summary.json", help="JSON output file")
    parser.add_argument("--report-output", default="pr_review_snapshot.md", help="Markdown report for PR comments")
    parser.add_argument("--use-llm", action="store_true", help="Enable local LLM enhancement if Ollama is present")
    parser.add_argument("--voice", default="Samantha", help="macOS text-to-speech voice name, such as Samantha")
    parser.add_argument("--speak", action="store_true", help="Read the short summary aloud with the selected macOS voice")
    args = parser.parse_args()

    result = analyze_pr(args.repo, base_ref=args.base, use_llm=args.use_llm)
    report_text = build_pr_report(result)
    Path(args.report_output).write_text(report_text, encoding="utf-8")

    output_path = Path(args.output)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"summary": result["summary"], "review_areas": result["review_areas"], "security_status": result["security"]["scan_status"]}, indent=2))
    print(f"PR-ready markdown report written to {args.report_output}")

    if args.speak:
        try:
            import subprocess
            subprocess.run(["say", "-v", args.voice, result["podcast"]], check=False)
            print(f"Spoken with macOS voice: {args.voice}")
        except FileNotFoundError:
            print("macOS say command not available; voice playback skipped.")


if __name__ == "__main__":
    main()
