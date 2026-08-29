"""화별 LLM JSON을 분리하고 전체 작품 기준 ID로 정규화한다.

역할 분담
- id_handler.py: character / worldview rule 처리
- split_idmanager.py: event / time / location 처리 및 전체 참조 ID 치환
"""

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .id_handler import handle_ids


NORMALIZED_FILES = {
    "characters": "characters.json",
    "events": "events.json",
    "worldview_rules": "rules.json",
    "times": "times.json",
    "locations": "locations.json",
}

ID_CONFIG = {
    "events": {"field": "event_id", "prefix": "EVENT"},
    "times": {"field": "time_id", "prefix": "TIME"},
    "locations": {"field": "location_id", "prefix": "LOCATION"},
}


def load_json(path: str | Path) -> Any:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_or_empty_list(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []

    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"{path}의 최상위 구조는 JSON 배열이어야 합니다.")

    return data


def validate_raw_json(data: dict) -> None:
    """1차 LLM 결과가 normalization 가능한 기본 구조인지 확인한다."""
    if not isinstance(data, dict):
        raise ValueError("Raw JSON의 최상위 구조는 객체여야 합니다.")

    expected_fields = {
        "characters",
        "events",
        "worldview_rules",
        "times",
        "locations",
    }

    missing = expected_fields - data.keys()
    if missing:
        raise ValueError(
            "Raw JSON에 필요한 필드가 없습니다: " + ", ".join(sorted(missing))
        )

    for field in expected_fields:
        if not isinstance(data[field], list):
            raise ValueError(f"'{field}' 필드는 배열이어야 합니다.")


def extract_number(identifier: str, prefix: str) -> int:
    """EVENT_012 -> 12"""
    match = re.match(rf"^{re.escape(prefix)}_(\d+)$", identifier)
    if not match:
        raise ValueError(f"잘못된 ID 형식입니다: {identifier}")
    return int(match.group(1))


def get_next_id_number(
    existing_items: list[dict],
    id_field: str,
    prefix: str,
) -> int:
    """기존 통합 JSON에서 다음에 사용할 순번을 구한다."""
    max_number = 0

    for item in existing_items:
        identifier = item.get(id_field)
        if not identifier:
            continue

        try:
            number = extract_number(identifier, prefix)
        except ValueError:
            continue

        max_number = max(max_number, number)

    return max_number + 1


def build_sequential_id_map(
    new_items: list[dict],
    existing_items: list[dict],
    id_field: str,
    prefix: str,
) -> dict[str, str]:
    """이번 화의 local ID -> 작품 전체 global ID 매핑을 만든다."""
    next_number = get_next_id_number(existing_items, id_field, prefix)
    id_map: dict[str, str] = {}

    for item in new_items:
        local_id = item.get(id_field)
        if not local_id:
            raise ValueError(f"{id_field}가 없는 데이터가 있습니다.")

        if local_id in id_map:
            raise ValueError(f"한 JSON 안에서 ID가 중복되었습니다: {local_id}")

        id_map[local_id] = f"{prefix}_{next_number:03d}"
        next_number += 1

    return id_map


def replace_references_recursive(
    value: Any,
    id_maps: list[dict[str, str]],
) -> Any:
    """dict/list 내부의 local ID 문자열을 global ID로 재귀 치환한다."""
    if isinstance(value, str):
        for id_map in id_maps:
            if value in id_map:
                return id_map[value]
        return value

    if isinstance(value, list):
        return [replace_references_recursive(item, id_maps) for item in value]

    if isinstance(value, dict):
        return {
            key: replace_references_recursive(item, id_maps)
            for key, item in value.items()
        }

    return value


def normalize_items(
    items: list[dict],
    all_id_maps: list[dict[str, str]],
    episode_number: int,
    id_field: str,
) -> list[dict]:
    """event/time/location의 ID와 내부 참조 ID를 치환하고 출처를 기록한다."""
    normalized: list[dict] = []

    for item in items:
        copied = deepcopy(item)
        local_id = copied.get(id_field)

        copied = replace_references_recursive(copied, all_id_maps)
        copied["source_episode"] = episode_number

        if local_id:
            copied["source_local_id"] = local_id

        normalized.append(copied)

    return normalized


def normalize_episode(
    raw_json_path: str | Path,
    normalized_dir: str | Path,
    episode_number: int,
) -> dict:
    """화별 LLM 분석 결과 하나를 전체 작품 통합 JSON에 편입한다.

    처리 순서
    1. raw JSON 및 기존 통합 JSON 로드
    2. id_handler로 character / rule 처리
    3. event / time / location의 연속 ID 생성
    4. 모든 객체 내부의 character/rule/event/time/location 참조 ID 치환
    5. 종류별 통합 JSON 저장
    """
    if episode_number < 1:
        raise ValueError("episode_number는 1 이상의 정수여야 합니다.")

    raw_json_path = Path(raw_json_path)
    normalized_dir = Path(normalized_dir)

    raw_data = load_json(raw_json_path)
    validate_raw_json(raw_data)

    existing = {
        category: load_or_empty_list(normalized_dir / filename)
        for category, filename in NORMALIZED_FILES.items()
    }

    # Character / Rule은 id_handler가 전담한다.
    handled = handle_ids(
        new_characters=raw_data["characters"],
        new_rules=raw_data["worldview_rules"],
        existing_characters=existing["characters"],
        existing_rules=existing["worldview_rules"],
        episode_number=episode_number,
    )

    character_map = handled["character_id_map"]
    rule_map = handled["rule_id_map"]

    event_map = build_sequential_id_map(
        raw_data["events"],
        existing["events"],
        ID_CONFIG["events"]["field"],
        ID_CONFIG["events"]["prefix"],
    )
    time_map = build_sequential_id_map(
        raw_data["times"],
        existing["times"],
        ID_CONFIG["times"]["field"],
        ID_CONFIG["times"]["prefix"],
    )
    location_map = build_sequential_id_map(
        raw_data["locations"],
        existing["locations"],
        ID_CONFIG["locations"]["field"],
        ID_CONFIG["locations"]["prefix"],
    )

    all_id_maps = [
        character_map,
        rule_map,
        event_map,
        time_map,
        location_map,
    ]

    normalized_events = normalize_items(
        raw_data["events"],
        all_id_maps,
        episode_number,
        id_field="event_id",
    )
    normalized_times = normalize_items(
        raw_data["times"],
        all_id_maps,
        episode_number,
        id_field="time_id",
    )
    normalized_locations = normalize_items(
        raw_data["locations"],
        all_id_maps,
        episode_number,
        id_field="location_id",
    )

    # Character / Rule의 global ID는 id_handler에서 이미 확정된다.
    # 현재 화의 local ID map을 기존 통합 데이터 전체에 다시 적용하면
    # CHAR_001, RULE_001 같은 기존 global ID까지 잘못 치환될 수 있으므로
    # 여기서는 id_handler 결과를 그대로 저장한다.
    normalized_characters = handled["characters"]
    normalized_rules = handled["rules"]

    merged_events = existing["events"] + normalized_events
    merged_times = existing["times"] + normalized_times
    merged_locations = existing["locations"] + normalized_locations

    save_json(normalized_characters, normalized_dir / "characters.json")
    save_json(merged_events, normalized_dir / "events.json")
    save_json(normalized_rules, normalized_dir / "rules.json")
    save_json(merged_times, normalized_dir / "times.json")
    save_json(merged_locations, normalized_dir / "locations.json")

    return {
        "episode_number": episode_number,
        "characters_added": len(handled["new_character_ids"]),
        "events_added": len(normalized_events),
        "rules_added": len(handled["new_rule_ids"]),
        "times_added": len(normalized_times),
        "locations_added": len(normalized_locations),
        "id_maps": {
            "characters": character_map,
            "events": event_map,
            "rules": rule_map,
            "times": time_map,
            "locations": location_map,
        },
    }
