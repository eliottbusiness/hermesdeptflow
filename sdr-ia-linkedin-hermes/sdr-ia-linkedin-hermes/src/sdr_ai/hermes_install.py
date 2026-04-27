from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .config import ClientConfig
from .onboarding import write_memory_file


def repo_root() -> Path:
    candidates = []
    if os.getenv("SDR_AI_REPO_ROOT"):
        candidates.append(Path(os.environ["SDR_AI_REPO_ROOT"]).expanduser())
    candidates.extend([Path.cwd(), Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1]])
    for candidate in candidates:
        if (candidate / "hermes" / "skills").exists():
            return candidate
    raise FileNotFoundError(
        "Impossible de trouver hermes/skills. Lance la commande depuis la racine du repo "
        "ou exporte SDR_AI_REPO_ROOT=/chemin/du/repo."
    )


def _copy_skill_tree(src_root: Path, dest_root: Path, exclude: set[str] | None = None) -> list[Path]:
    exclude = exclude or set()
    written: list[Path] = []
    dest_root.mkdir(parents=True, exist_ok=True)
    for skill_dir in src_root.iterdir():
        if not skill_dir.is_dir() or skill_dir.name in exclude:
            continue
        target = dest_root / skill_dir.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target)
        written.append(target)
    return written


def install_skills(hermes_home: str | Path = "~/.hermes") -> list[Path]:
    home = Path(hermes_home).expanduser()
    dest = home / "skills" / "sales"
    src = repo_root() / "hermes" / "skills"
    return _copy_skill_tree(src, dest)


def ensure_hermes_profile(cfg: ClientConfig) -> None:
    if shutil.which("hermes") is None:
        return
    slug = cfg.hermes.profile_slug
    listed = subprocess.run(["hermes", "profile", "list"], text=True, capture_output=True, check=False)
    if listed.returncode == 0 and slug in listed.stdout:
        return
    subprocess.run(["hermes", "profile", "create", slug, "--clone"], check=False)


def install_client_profile_files(cfg: ClientConfig, hermes_home: str | Path = "~/.hermes") -> Path:
    home = Path(hermes_home).expanduser()
    profile_dir = home / "profiles" / cfg.hermes.profile_slug
    profile_dir.mkdir(parents=True, exist_ok=True)
    write_memory_file(cfg, profile_dir / "MEMORY.md")
    skills_dir = profile_dir / "skills" / "sales"
    _copy_skill_tree(repo_root() / "hermes" / "skills", skills_dir, exclude={"client-onboarding"})
    return profile_dir
