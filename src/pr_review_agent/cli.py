from __future__ import annotations

import json
from pathlib import Path

from pr_review_agent.analyzer import analyze_pr, build_pr_report
from pr_review_agent.ollama_client import maybe_enrich_with_ollama


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Local pull request reviewer")
    parser.add_argument("--repo", required=True, help="Path to the git repository to inspect")
    parser.add_argument("--base", default="main", help="Base branch for the PR diff")
    parser.add_argument("--output", default="pr_review_report.json", help="Path to write the JSON report")
    parser.add_argument("--markdown-output", default="pr_review_report.md", help="Path to write a markdown summary")
    parser.add_argument("--use-llm", action="store_true", help="Use a local Ollama model if it is running")
    parser.add_argument("--voice", default="Samantha", help="macOS text-to-speech voice name, such as Samantha")
    parser.add_argument("--speak", action="store_true", help="Read the short podcast summary aloud")
    parser.add_argument("--use-kokoro", action="store_true", help="Use local Kokoro TTS to generate podcast audio")
    args = parser.parse_args()

    result = analyze_pr(args.repo, base_ref=args.base, use_llm=args.use_llm)
    if args.use_llm:
        result = maybe_enrich_with_ollama(result)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    md_path = Path(args.markdown_output)
    md_path.write_text(build_pr_report(result), encoding="utf-8")

    print(f"Wrote JSON report to {output_path}")
    print(f"Wrote markdown report to {md_path}")
    print("\nSummary:")
    print(result["summary"])

    if args.speak:
        import subprocess
        try:
            if args.use_kokoro:
                # Try Kokoro first if requested
                from pr_review_agent.kokoro_client import is_kokoro_available, synthesize

                if is_kokoro_available():
                    out = "demo_voice_kokoro.wav"
                    try:
                        synthesize(result.get("podcast", ""), out_path=out)
                        # play via afplay on macOS
                        if subprocess.run(["which", "afplay"], capture_output=True).returncode == 0:
                            subprocess.run(["afplay", out], check=False)
                        print(f"Generated and played Kokoro audio: {out}")
                        raise SystemExit(0)
                    except Exception as exc:
                        print(f"Kokoro synthesis failed: {exc}. Falling back to macOS say.")

            subprocess.run(["say", "-v", args.voice, result["podcast"]], check=False)
            print(f"Spoken with macOS voice: {args.voice}")
        except FileNotFoundError:
            print("macOS say command not available; voice playback skipped.")


if __name__ == "__main__":
    main()
