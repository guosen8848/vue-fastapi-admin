from pathlib import Path
from uuid import uuid4


STORAGE_ROOT = Path("storage")
EXAM_BANK_STORAGE_DIR = STORAGE_ROOT / "exam" / "banks"


def save_bank_source_file(file_name: str, file_bytes: bytes):
    suffix = Path(file_name).suffix.lower() or ".xlsx"
    EXAM_BANK_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{suffix}"
    relative_path = Path("exam") / "banks" / stored_name
    absolute_path = STORAGE_ROOT / relative_path
    absolute_path.write_bytes(file_bytes)
    return {
        "file_name": file_name,
        "file_path": relative_path.as_posix(),
        "absolute_path": absolute_path,
    }


def remove_stored_file(relative_path: str | None):
    if not relative_path:
        return

    file_path = STORAGE_ROOT / relative_path
    if file_path.exists():
        file_path.unlink()
