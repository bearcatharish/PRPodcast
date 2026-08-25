# PR Review Agent

PR Review Agent is a local Python tool that reviews the changes on a Git branch. It compares `HEAD` with a base branch, identifies review hotspots, scans for common security signals and dependency changes, and produces a JSON report, a Markdown snapshot, and a short podcast-style summary.

It runs entirely on your machine. The default analyzer does not require a cloud API or an LLM.

## Features

- Compares a checked-out branch with a configurable base branch.
- Summarizes recent commit messages and changed files.
- Classifies review areas such as backend, UI, database, pipeline, testing, and general maintenance.
- Detects dependency names in common Python and JavaScript configuration files.
- Scans changed files for security-sensitive patterns that need human review.
- Writes JSON and Markdown reports.
- Optionally enriches the summary with a local Ollama model.
- Optionally reads the podcast summary with macOS `say`.
- Includes experimental Kokoro TTS support for local audio generation.
- Provides both a command-line interface and a local Flask web UI.

## Repository layout

```text
src/pr_review_agent/   Application package, CLI, web UI, and integrations
tests/                 Pytest tests
pyproject.toml         Package metadata and dependencies
kokoro/                Optional Kokoro checkout referenced as a Git submodule
.gitignore             Local environments, caches, reports, and audio exclusions
```

Generated reports and audio are intentionally not stored in Git. The optional Kokoro model and Python environments should also remain local.

## Requirements

- Python 3.9 or newer for the main project.
- Git, because the analyzer reads branch history and diffs.
- macOS `say` only if you want spoken output through the default voice path.
- Python 3.10 or newer for the optional Kokoro integration.
- Ollama and the `llama3.1:8b` model only if you want local LLM enrichment.

## Run locally

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest
```

The expected result is the analyzer test passing without requiring Ollama, Kokoro, or generated audio files.

## CLI usage

The target repository must already be a Git repository, and the branch to review must be checked out:

```bash
cd /path/to/repository-to-review
git status
git branch --show-current
```

From the PR Review Agent repository, generate both report formats:

```bash
pr-review-agent \
	--repo /path/to/repository-to-review \
	--base main \
	--output /tmp/pr_review_report.json \
	--markdown-output /tmp/pr_review_report.md
```

The CLI compares the target repository's `HEAD` with `main` by default. Use another branch with `--base release` or a different base ref.

### CLI options

| Option | Purpose |
| --- | --- |
| `--repo PATH` | Required path to the repository being reviewed |
| `--base REF` | Base branch or ref; defaults to `main` |
| `--output PATH` | JSON output path; defaults to `pr_review_report.json` |
| `--markdown-output PATH` | Markdown output path; defaults to `pr_review_report.md` |
| `--use-llm` | Ask the local Ollama service to enrich the result |
| `--speak` | Read the podcast summary aloud |
| `--voice NAME` | macOS voice name; defaults to `Samantha` |
| `--use-kokoro` | Try Kokoro audio first, then fall back to macOS `say` |

Example with spoken output:

```bash
pr-review-agent --repo /path/to/repository-to-review --base main --speak --voice Samantha
```

## Local web UI

Start the Flask interface from the project root while the virtual environment is active:

```bash
python -m pr_review_agent.web --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>, enter the target repository path and base branch, then choose whether to use Ollama or Kokoro. The page renders the Markdown snapshot and can invoke server-side macOS speech.

The server binds to localhost by default. Keep it local: the form accepts filesystem paths and runs Git analysis against paths supplied by the user.

Use another port if `8000` is busy:

```bash
python -m pr_review_agent.web --host 127.0.0.1 --port 8001
```

## Optional Ollama enrichment

The normal analyzer uses built-in heuristics. To enable local LLM enrichment, install and start Ollama, then download the model used by the client:

```bash
ollama serve
ollama pull llama3.1:8b
```

Run the CLI with `--use-llm` or select the Ollama option in the web UI. The application continues with its normal local summary when Ollama is unavailable or the model is not installed. The client connects to `http://localhost:11434/api/generate`.

## Optional Kokoro TTS

Kokoro is an Apache-2.0 licensed, open-weight 82M-parameter TTS model. This repository keeps Kokoro separate from the main Python environment because it requires Python 3.10 or newer and heavyweight ML dependencies.

The integration in `src/pr_review_agent/kokoro_client.py` looks for:

1. The directory named by `KOKORO_PATH`.
2. A `kokoro/` directory inside `src/`.
3. The project-root `kokoro/` checkout.

The checkout must provide `samples/synthesize.py` for the wrapper to report itself as available. If it is unavailable, `--use-kokoro` falls back to macOS `say`.

For a separate Kokoro environment:

```bash
python3.10 -m venv .kokoro-venv
source .kokoro-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install kokoro soundfile
python -m pip install "misaki[en]"
```

Then point the integration at a compatible checkout if needed:

```bash
export KOKORO_PATH=/path/to/kokoro
pr-review-agent --repo /path/to/repository-to-review --speak --use-kokoro
```

Kokoro audio is written as a local `demo_voice_kokoro.wav` file and is ignored by Git.

## How analysis works

1. Read changed paths from the target repository's Git diff.
2. Fall back to a recent file sample when no diff is available.
3. Summarize up to the three latest relevant commit messages.
4. Detect dependency names and classify review areas.
5. Scan changed text for known security-sensitive patterns.
6. Build the JSON result, Markdown snapshot, and podcast text.

The security scan is a review aid, not a replacement for a security audit. Detected patterns are signals for human inspection and may include false positives.

## Troubleshooting

- **No changed files:** Confirm the target branch has commits beyond the selected base and that the base ref exists locally.
- **Base ref error:** Fetch the target repository's branches or pass an existing ref with `--base`.
- **Ollama unavailable:** Start Ollama and verify `ollama pull llama3.1:8b`; analysis still works without it.
- **Speech unavailable:** `--speak` requires macOS `say`; omit it to generate reports without audio.
- **Kokoro unavailable:** Check `KOKORO_PATH`, Python 3.10+, dependencies, and the required `samples/synthesize.py` script.
- **Port in use:** Start the web UI with another port, such as `--port 8001`.

## Development

Install the editable development package with `python -m pip install -e ".[dev]"`, run `pytest`, and keep local environments, caches, generated reports, audio, and model files out of commits. The `kokoro/` directory is an optional nested repository and should not be replaced with a copied model checkout.

