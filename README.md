# PR Review Agent

A local tool that inspects a Git repository (on your machine), summarizes the changes on the current branch compared to a base branch, highlights security signals and dependency changes, and produces a short, PR-ready report plus a concise podcast-style narration.

This repository contains a small CLI and a minimal local web UI you can run on a machine to select a repository path and generate the report.

## Where the project sits locally

- Code and CLI: `src/pr_review_agent`
- Generated reports (examples): `pr_review_report.md`, `pr_review_report.json`

## Important libraries

- `requests` — used by the optional local LLM integration client
- `Flask` — small web UI to run the analyzer from a browser (optional)
- `pytest` — test suite

All dependencies are listed in `pyproject.toml`.

## Optional local LLMs

The project can optionally enrich summaries using a local Ollama model. Supported example:

- `llama3.1:8b`

To prepare Ollama:

```bash
# start the Ollama server (if installed)
ollama serve
# download a model
ollama pull llama3.1:8b
```

If Ollama is not available the analyzer still runs with the built-in heuristics.

## Quick install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Run the CLI

Generate a PR-style report for a local repository (must already be a git repo with the branch checked out):

```bash
pr-review-agent --repo /path/to/local/repo --base main --output pr_review_report.json --markdown-output pr_review_report.md
```

Notes:
- Make sure you run this while the branch you want analyzed is the currently checked-out branch inside `/path/to/local/repo` (use `git status` / `git branch`).
- The tool compares `HEAD` against `--base` (default `main`).

## Run the local web UI (select repo and branch via browser)

The project includes a small Flask app that exposes a form where you can enter a local repo path and base branch. Start it like this:

```bash
# from project root
source .venv/bin/activate
python -m pr_review_agent.web --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000 in your browser
```

The UI will:
- accept a local filesystem path to the repository
- accept a base branch to compare against (default `main`)
- run the analyzer and render the short PR snapshot
- provide a server-side "Speak" action that invokes the macOS `say` TTS (if available) to read the short podcast text

Security note: the web UI runs locally only and executes analysis on paths you provide. Do not expose this service to untrusted networks.

## How the analyzer works (short)

1. Collects changed files between `HEAD` and the base branch.
2. Summarizes recent commit messages for context.
3. Scans changed files for known security patterns and dependency changes.
4. Classifies hotspots (UI, backend, database, pipeline).
5. Produces a short PR-ready markdown and a one-paragraph podcast-style summary.

## Branch and podcast checklist

1. Ensure the local repo has the branch you want to analyze checked out:

```bash
cd /path/to/local/repo
git checkout feature/your-branch
git status
```

2. Run the analyzer (CLI or web UI) while on that branch — the tool reads `HEAD` and compares to `--base`.

3. If you want the podcast narration, either use the `--speak` flag for the CLI (macOS `say`) or use the web UI and click the `Speak` action.

## Example: run from CLI and serve the markdown file locally

```bash
pr-review-agent --repo /Users/me/projects/myrepo --base main --markdown-output /tmp/my_pr.md
python -m http.server --directory /tmp 8001
# open http://127.0.0.1:8001/my_pr.md
```

## Troubleshooting & tips

- If the tool finds no changed files, ensure your working tree has commits on the feature branch.
- If Ollama calls fail, check `http://localhost:11434` and that the model is pulled.
- To change the spoken voice on macOS, use `--voice Samantha` or another installed voice.

---

If you'd like, I can also add a one-click GitHub pull-request comment formatter (single-paragraph) or commit a small web UI template to this repo now.

## Kokoro TTS (optional)

This repository includes optional integration with Kokoro, an open-weight TTS model (82M parameters) that can run locally and offline. Kokoro is Apache-2.0 licensed.

Important notes:
- Kokoro and some of its language-specific dependencies require Python 3.10 or newer. If your project's venv uses Python 3.9, create a separate venv for Kokoro.
- The project contains a thin wrapper `src/pr_review_agent/kokoro_client.py` and CLI/web flags to use Kokoro when available (`--use-kokoro` and a checkbox in the web UI). The wrapper looks for a `kokoro/` checkout next to this project or an explicit `KOKORO_PATH` environment variable.

Quick setup (recommended in a separate Python 3.10+ environment):

```bash
# create a venv with Python 3.10+
python3.10 -m venv .kokoro-venv
source .kokoro-venv/bin/activate

# install kokoro and audio dependencies
pip install --upgrade pip
pip install kokoro soundfile
# optional: English phonemization support
pip install misaki[en]
```

If you prefer, you can clone the Kokoro GitHub repo next to this project and set `KOKORO_PATH`:

```bash
git clone https://github.com/hexgrad/kokoro.git ../kokoro
export KOKORO_PATH="$(pwd)/../kokoro"
```

Generate audio via the CLI (if Kokoro is installed and available):

```bash
python -m pr_review_agent.cli --repo /path/to/repo --speak --use-kokoro
```

If Kokoro is not available, the tool falls back to the macOS `say` TTS command for local demo audio.

