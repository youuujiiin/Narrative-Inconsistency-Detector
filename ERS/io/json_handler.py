"""json 입출력"""
import json
from pathlib import Path
from typing import Any


def load_json(file_path: str | Path) -> Any:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"JSON 파일을 찾을 수 없습니다: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(
    data: Any,
    file_path: str | Path,
) -> None:
    path = Path(file_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )