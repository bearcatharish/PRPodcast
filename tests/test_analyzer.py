import subprocess
from pathlib import Path

from pr_review_agent.analyzer import analyze_pr


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def test_analyze_pr_detects_security_summary_and_review_areas(tmp_path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")

    (repo / "README.md").write_text("Demo repository\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial commit")
    _git(repo, "branch", "-M", "main")

    _git(repo, "checkout", "-b", "feature/secure-api")
    (repo / "requirements.txt").write_text("requests==2.31.0\nfastapi==0.111.0\n")
    (repo / "app.py").write_text("import subprocess\n\nSECRET = 'abc123'\nsubprocess.run(['echo', 'hello'])\n")
    (repo / "migrations").mkdir()
    (repo / "migrations" / "001_init.sql").write_text("CREATE TABLE users (id INT);\n")
    (repo / ".github").mkdir()
    (repo / ".github" / "workflows").mkdir()
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n")

    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add API and DB changes")

    result = analyze_pr(repo, base_ref="main")

    assert "summary" in result
    assert "security" in result
    assert "important_libraries" in result
    assert any("backend" in area.lower() or "pipeline" in area.lower() or "database" in area.lower() for area in result["review_areas"])
    assert any("fastapi" in lib.lower() for lib in result["important_libraries"])
    assert "podcast" in result
    assert "subprocess" in result["security"]["risk_signals"]
