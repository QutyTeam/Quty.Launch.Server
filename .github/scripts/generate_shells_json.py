#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
from pathlib import Path

# ============================================================
# НАСТРОЙКИ
# ============================================================

REPO_OWNER = "Sanya2104"
REPO_NAME = "Quty.Launch.Server"
BRANCH = "main"
BASE_RAW_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}"

SHELLS_DIR = Path("store/shells")
OUTPUT_FILE = Path("store/shells.json")

SUPPORTED_EXTENSIONS = {".qutyshell", ".qsp", ".qutyshellpack"}


# ============================================================
# ХЕЛПЕРЫ
# ============================================================

def get_file_size_readable(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def find_qutyshell(folder: Path) -> Path | None:
    candidates = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not candidates:
        return None
    for c in candidates:
        if c.stem == folder.name:
            return c
    return candidates[0]


def compute_sha256(path: Path) -> str:
    """SHA-256 пакета — ядро сверяет его перед установкой оболочки."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_git_commit_date(folder_path: str) -> str:
    """
    Получает дату последнего коммита для указанной папки.
    Формат: YYYY-MM-DD
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=short", "--", folder_path],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ============================================================
# ОСНОВНАЯ ЛОГИКА
# ============================================================

def generate() -> int:
    shells = []
    errors = 0

    if not SHELLS_DIR.exists():
        print(f"❌ {SHELLS_DIR} не найдена")
        return 1

    for folder in sorted(SHELLS_DIR.iterdir()):
        if not folder.is_dir():
            continue

        shell_id = folder.name
        manifest_path = folder / "manifest.json"

        if not manifest_path.exists():
            print(f"⚠️  {shell_id}: нет manifest.json")
            errors += 1
            continue

        qutyshell = find_qutyshell(folder)
        if not qutyshell:
            print(f"⚠️  {shell_id}: нет .qutyshell файла")
            errors += 1
            continue

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            print(f"❌ {shell_id}: ошибка чтения manifest.json: {e}")
            errors += 1
            continue

        # URL-ы
        preview_file = manifest.get("preview", "preview.png")
        preview_url = f"{BASE_RAW_URL}/store/shells/{shell_id}/{preview_file}"
        download_url = f"{BASE_RAW_URL}/store/shells/{shell_id}/{qutyshell.name}"

        # Размер файла
        file_size = get_file_size_readable(qutyshell.stat().st_size)

        # Дата из Git (коммит для этой папки)
        date_published = get_git_commit_date(f"store/shells/{shell_id}")

        shell_obj = {
            "id": shell_id,
            "name": shell_id,
            "displayName": manifest.get("name", shell_id),
            "author": manifest.get("author", "Unknown"),
            "version": manifest.get("version", "0.0.0"),
            "previewUrl": preview_url,
            "downloadUrl": download_url,
            "fileSize": file_size,
            "sha256": compute_sha256(qutyshell),
            "minQutyLaunchVersion": manifest.get("minQutyLaunchVersion", "0.0.0"),
            "orientation": manifest.get("orientation"),
            "repoUrl": manifest.get("repoUrl"),
            "telegram": manifest.get("telegram"),
            "datePublished": date_published,
        }

        shells.append(shell_obj)
        print(f"✅ {shell_id}: {shell_obj['displayName']} v{shell_obj['version']} ({date_published})")

    output = {"shells": shells}
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" — фиксированные переводы строк: файл подписывается, и на
    # Windows, и на Linux байты должны совпадать с тем, что уйдёт на CDN.
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"\n📦 Записано {len(shells)} оболочек в {OUTPUT_FILE}")
    if errors > 0:
        print(f"⚠️  Пропущено: {errors}")
    return 0


if __name__ == "__main__":
    sys.exit(generate())