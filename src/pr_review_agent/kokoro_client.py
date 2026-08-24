from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional


def _find_kokoro_root() -> Optional[Path]:
    # Respect explicit env var
    env = os.environ.get("KOKORO_PATH")
    if env:
        p = Path(env)
        if p.exists():
            return p

    # Check common locations: sibling folder named kokoro, or installed package
    here = Path(__file__).resolve().parent.parent
    candidate = here / "kokoro"
    if candidate.exists():
        return candidate

    # Not found locally
    return None


def is_kokoro_available() -> bool:
    root = _find_kokoro_root()
    if root is None:
        return False
    synth_script = root / "samples" / "synthesize.py"
    return synth_script.exists()


def synthesize(text: str, out_path: str | Path, model_path: Optional[str] = None, timeout: int = 120) -> Path:
    """Synthesize `text` with a local Kokoro checkout.

    - Looks for KOKORO_PATH env var or a `kokoro/` sibling directory.
    - Calls `samples/synthesize.py --model <model> --text <text> --out <out>`.

    Returns Path to the generated file.
    """
    root = _find_kokoro_root()
    if root is None:
        raise FileNotFoundError("Kokoro repository not found. Set KOKORO_PATH or place kokoro/ next to this project")

    synth_script = root / "samples" / "synthesize.py"
    if not synth_script.exists():
        raise FileNotFoundError(f"Kokoro synth script not found at {synth_script}")

    out = Path(out_path)
    cmd = ["python", str(synth_script), "--text", text, "--out", str(out)]
    if model_path:
        cmd.extend(["--model", str(model_path)])

    subprocess.run(cmd, check=True, cwd=str(root), timeout=timeout)
    return out
