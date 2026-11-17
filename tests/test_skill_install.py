"""The public setup command installs usable skills and preserves local edits."""

import json
from pathlib import Path

import pytest

from genome.cli import main


def test_skill_install_and_repeat(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    main(["skill", "install", "--json"])
    result = json.loads(capsys.readouterr().out)
    assert [item["agent"] for item in result["installations"]] == ["Codex", "Claude Code"]
    for item in result["installations"]:
        text = Path(item["path"]).read_text(encoding="utf-8")
        assert "name: muvi" in text and "muvi ... --json" in text
        assert item["status"] == "installed"
    main(["skill", "install", "--json"])
    assert all(item["status"] == "unchanged"
               for item in json.loads(capsys.readouterr().out)["installations"])


def test_skill_install_preserves_existing_edits(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    target = tmp_path / ".claude" / "skills" / "muvi" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("My custom instructions", encoding="utf-8")
    with pytest.raises(SystemExit, match="2"):
        main(["skill", "install"])
    assert "--force" in capsys.readouterr().err
    assert target.read_text(encoding="utf-8") == "My custom instructions"
    assert not (tmp_path / ".agents").exists()
    main(["skill", "install", "--agent", "claude", "--force", "--json"])
    result = json.loads(capsys.readouterr().out)
    assert len(result["installations"]) == 1
    assert "name: muvi" in target.read_text(encoding="utf-8")
