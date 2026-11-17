"""Install the packaged skill without network access or audio dependencies."""

import os
import tempfile
from importlib.resources import files
from pathlib import Path

from genome import __version__


def install_skill(agent="all", force=False):
    bundled = files("genome").joinpath("SKILL.md")
    # Source checkouts keep the same canonical file in the discoverable skills tree.
    content = (bundled.read_bytes() if bundled.is_file() else
               (Path(__file__).parent.parent / "skills" / "muvi" / "SKILL.md").read_bytes())
    locations = {"codex": ("Codex", ".agents"), "claude": ("Claude Code", ".claude")}
    selected = locations if agent == "all" else {agent: locations[agent]}
    targets = [(name, Path.home() / folder / "skills" / "muvi" / "SKILL.md")
               for name, folder in selected.values()]
    # Check every destination before changing any of them.
    for _, target in targets:
        if target.is_symlink() or target.parent.is_symlink():
            raise ValueError(f"Skill path is a symlink: {target}. Update its source directly.")
        if target.exists() and target.read_bytes() != content and not force:
            raise ValueError(f"A different skill exists at {target}. Use --force to replace it.")
    installed = []
    for name, target in targets:
        status = "unchanged"
        if not target.exists() or target.read_bytes() != content:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(content)
                os.replace(temporary, target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            status = "installed"
        installed.append({"agent": name, "path": str(target), "status": status})
    return {"skill": "muvi", "version": __version__, "installations": installed,
            "next_step": "Start a new agent chat and ask about a local audio file."}
