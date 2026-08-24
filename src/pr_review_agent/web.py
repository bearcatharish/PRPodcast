from __future__ import annotations

from pathlib import Path
import subprocess
import html
from typing import Any

from flask import Flask, request, redirect, url_for, render_template_string, jsonify

from pr_review_agent.analyzer import analyze_pr, build_pr_report
from pr_review_agent.ollama_client import maybe_enrich_with_ollama

app = Flask(__name__)

INDEX_HTML = """
<!doctype html>
<title>PR Review Agent - Local UI</title>
<h1>PR Review Agent (local)</h1>
<form method=post>
  <label>Local repo path: <input name=repo size=60 value="{{ repo|default('') }}"></label><br>
  <label>Base branch: <input name=base value="{{ base|default('main') }}"></label><br>
  <label>Use local LLM (Ollama): <input type=checkbox name=use_llm {{ 'checked' if use_llm else '' }}></label><br>
    <label>Use local Kokoro TTS: <input type=checkbox name=use_kokoro {{ 'checked' if use_kokoro else '' }}></label><br>
  <input type=submit value="Analyze">
</form>
{% if report %}
  <h2>PR Snapshot</h2>
  <pre>{{ report }}</pre>
  <form action="{{ url_for('speak') }}" method="post">
    <input type=hidden name=podcast value="{{ podcast }}">
    <input type=submit value="Speak (server-side)">
  </form>
{% endif %}
"""


@app.route('/', methods=['GET', 'POST'])
def index():
    report = None
    podcast = ''
    repo = ''
    base = 'main'
    use_llm = False
    use_kokoro = False
    if request.method == 'POST':
        repo = request.form.get('repo', '').strip()
        base = request.form.get('base', 'main').strip()
        use_llm = bool(request.form.get('use_llm'))
        use_kokoro = bool(request.form.get('use_kokoro'))
        if not repo:
            report = 'Error: please provide a local repository path'
        else:
            try:
                result = analyze_pr(repo, base_ref=base, use_llm=use_llm)
                if use_llm:
                    result = maybe_enrich_with_ollama(result)
                report = build_pr_report(result)
                podcast = result.get('podcast', '')
                if use_kokoro and podcast:
                    try:
                        from pr_review_agent.kokoro_client import is_kokoro_available, synthesize
                        if is_kokoro_available():
                            out = Path(repo) / 'demo_voice_kokoro.wav'
                            synthesize(podcast, out_path=out)
                            report += f"\n\nKokoro audio generated at: {out}"
                    except Exception as exc:
                        report += f"\n\nKokoro synthesis failed: {exc}"
            except Exception as exc:
                report = f'Analysis failed: {html.escape(str(exc))}'
    return render_template_string(INDEX_HTML, report=report, repo=repo, base=base, use_llm=use_llm, use_kokoro=use_kokoro, podcast=podcast)


@app.route('/speak', methods=['POST'])
def speak():
    podcast_text = request.form.get('podcast') or request.form.get('podcast_text') or ''
    voice = request.form.get('voice', 'Samantha')
    if not podcast_text:
        return jsonify({'status': 'error', 'message': 'No podcast text provided'}), 400
    try:
        # server-side TTS using macOS `say` (works only on macOS).
        subprocess.Popen(['say', '-v', voice, podcast_text])
        return jsonify({'status': 'ok', 'message': 'Speaking on server with voice ' + voice})
    except FileNotFoundError:
        return jsonify({'status': 'error', 'message': 'say command not found on server'}), 500


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Run local PR Review web UI')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8000, type=int)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args(argv)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
