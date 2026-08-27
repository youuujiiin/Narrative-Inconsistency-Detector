# json 파일 분리 및 id 정규화
import json
import re
from pathlib import Path
from typing import Any

from .character_resolver import resolve_characters


# ---------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------

NORMALIZED_FILES = {
    "characters": "characters.json",
    "events": "events.json",
    "worldview_rules": "rules.json",
    "times": "times.json",
    "locations": "locations.json",
}

ID_CONFIG = {
    "events": {
        "field": "event_id",
        "prefix": "EVENT",
    },
    "worldview_rules": {
        "field": "rule_id",
        "prefix": "RULE",
    },
    "times": {
        "field": "time_id",
        "prefix": "TIME",
    },
    "locations": {
        "field": "location_id",
        "prefix": "LOCATION",
    },
}


# ---------------------------------------------------------
# JSON 입출력
# ---------------------------------------------------------

def load_json(path: str | Path) -> Any:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"JSON 파일을 찾을 수 없습니다: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data: Any, path: str | Path) -> None:
    path = Path(path)

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


def load_or_empty_list(path: str | Path) -> list[dict]:
    """
    통합 JSON이 존재하면 읽고,
    아직 없다면 빈 배열을 반환한다.
    """
    path = Path(path)

    if not path.exists():
        return []

    data = load_json(path)

    if not isinstance(data, list):
        raise ValueError(
            f"{path}의 최상위 구조는 JSON 배열이어야 합니다."
        )

    return data


# ---------------------------------------------------------
# ID 관련
# ---------------------------------------------------------

def extract_number(
    identifier: str,
    prefix: str,
) -> int:
    """
    EVENT_012 -> 12
    RULE_003  -> 3
    """

    pattern = rf"^{re.escape(prefix)}_(\d+)$"
    match = re.match(pattern, identifier)

    if not match:
        raise ValueError(
            f"잘못된 ID 형식입니다: {identifier}"
        )

    return int(match.group(1))


def get_next_id_number(
    existing_items: list[dict],
    id_field: str,
    prefix: str,
) -> int:
    """
    기존 통합 JSON에서 가장 큰 ID 번호를 찾고
    다음 번호를 반환한다.

    예:
        EVENT_001
        EVENT_002
        EVENT_003

    -> 4
    """

    max_number = 0

    for item in existing_items:
        identifier = item.get(id_field)

        if not identifier:
            continue

        try:
            number = extract_number(
                identifier,
                prefix,
            )
        except ValueError:
            continue

        max_number = max(
            max_number,
            number,
        )

    return max_number + 1


def build_sequential_id_map(
    new_items: list[dict],
    existing_items: list[dict],
    id_field: str,
    prefix: str,
) -> dict[str, str]:
    """
    이번 화의 local ID를
    전체 작품 기준 global ID로 바꾸는 mapping을 만든다.

    예:
        이번 화 EVENT_001 -> EVENT_038
        이번 화 EVENT_002 -> EVENT_039
    """

    next_number = get_next_id_number(
        existing_items,
        id_field,
        prefix,
    )

    id_map = {}

    for item in new_items:
        local_id = item.get(id_field)

        if not local_id:
            continue

        global_id = (
            f"{prefix}_{next_number:03d}"
        )

        id_map[local_id] = global_id

        next_number += 1

    return id_map


# ---------------------------------------------------------
# ID 치환
# ---------------------------------------------------------

def replace_id(
    value: str | None,
    id_map: dict[str, str],
) -> str | None:

    if value is None:
        return None

    return id_map.get(
        value,
        value,
    )


def replace_id_list(
    values: list[str] | None,
    id_map: dict[str, str],
) -> list[str]:

    if not values:
        return []

    return [
        id_map.get(value, value)
        for value in values
    ]


def replace_references_recursive(
    value: Any,
    id_maps: list[dict[str, str]],
) -> Any:
    """
    JSON 객체 내부를 재귀적으로 탐색해서
    local ID가 발견되면 global ID로 치환한다.

    문자열 하나뿐 아니라
    list / dict 내부의 참조도 처리한다.
    """

    if isinstance(value, str):

        for id_map in id_maps:
            if value in id_map:
                return id_map[value]

        return value

    if isinstance(value, list):
        return [
            replace_references_recursive(
                item,
                id_maps,
            )
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: replace_references_recursive(
                item,
                id_maps,
            )
            for key, item in value.items()
        }

    return value


# ---------------------------------------------------------
# 일반 항목 정규화
# ---------------------------------------------------------

def normalize_items(
    items: list[dict],
    id_map: dict[str, str],
    all_id_maps: list[dict[str, str]],
) -> list[dict]:

    normalized = []

    for item in items:

        copied = item.copy()

        # item 자체의 ID + 내부 참조 ID를 함께 변경
        copied = replace_references_recursive(
            copied,
            all_id_maps,
        )

        normalized.append(copied)

    return normalized


# ---------------------------------------------------------
# Raw JSON 검증
# ---------------------------------------------------------

def validate_raw_json(data: dict) -> None:

    if not isinstance(data, dict):
        raise ValueError(
            "Raw JSON의 최상위 구조는 객체여야 합니다."
        )

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
            "Raw JSON에 필요한 필드가 없습니다: "
            + ", ".join(sorted(missing))
        )

    for field in expected_fields:

        if not isinstance(
            data[field],
            list,
        ):
            raise ValueError(
                f"'{field}' 필드는 배열이어야 합니다."
            )


# ---------------------------------------------------------
# 메인 Normalization
# ---------------------------------------------------------

def normalize_episode(
    raw_json_path: str | Path,
    normalized_dir: str | Path,
    episode_number: int | None = None,
) -> dict:
    """
    하나의 화별 LLM 분석 JSON을 정규화하고
    전체 작품 통합 JSON에 병합한다.

    처리 순서:

    1. Raw JSON 읽기
    2. 기존 통합 JSON 읽기
    3. 캐릭터 canonical ID 해결
    4. Event / Rule / Time / Location 새 ID 생성
    5. 내부 참조 ID 치환
    6. 각 통합 JSON 파일에 append
    """

    raw_json_path = Path(raw_json_path)
    normalized_dir = Path(normalized_dir)

    raw_data = load_json(
        raw_json_path
    )

    validate_raw_json(
        raw_data
    )

    # -----------------------------------------------------
    # 기존 통합 데이터
    # -----------------------------------------------------

    existing = {}

    for category, filename in NORMALIZED_FILES.items():

        existing[category] = load_or_empty_list(
            normalized_dir / filename
        )

    # -----------------------------------------------------
    # 신규 데이터
    # -----------------------------------------------------

    new_characters = raw_data["characters"]
    new_events = raw_data["events"]
    new_rules = raw_data["worldview_rules"]
    new_times = raw_data["times"]
    new_locations = raw_data["locations"]

    # -----------------------------------------------------
    # Character Resolution
    # -----------------------------------------------------

    character_result = resolve_characters(
        new_characters=new_characters,
        existing_characters=existing["characters"],
    )

    character_map = character_result["id_map"]

    normalized_new_characters = (
        character_result["new_characters"]
    )

    # -----------------------------------------------------
    # 일반 ID 생성
    # -----------------------------------------------------

    event_map = build_sequential_id_map(
        new_events,
        existing["events"],
        ID_CONFIG["events"]["field"],
        ID_CONFIG["events"]["prefix"],
    )

    rule_map = build_sequential_id_map(
        new_rules,
        existing["worldview_rules"],
        ID_CONFIG["worldview_rules"]["field"],
        ID_CONFIG["worldview_rules"]["prefix"],
    )

    time_map = build_sequential_id_map(
        new_times,
        existing["times"],
        ID_CONFIG["times"]["field"],
        ID_CONFIG["times"]["prefix"],
    )

    location_map = build_sequential_id_map(
        new_locations,
        existing["locations"],
        ID_CONFIG["locations"]["field"],
        ID_CONFIG["locations"]["prefix"],
    )

    all_id_maps = [
        character_map,
        event_map,
        rule_map,
        time_map,
        location_map,
    ]

    # -----------------------------------------------------
    # ID / 참조 정규화
    # -----------------------------------------------------

    normalized_events = normalize_items(
        new_events,
        event_map,
        all_id_maps,
    )

    normalized_rules = normalize_items(
        new_rules,
        rule_map,
        all_id_maps,
    )

    normalized_times = normalize_items(
        new_times,
        time_map,
        all_id_maps,
    )

    normalized_locations = normalize_items(
        new_locations,
        location_map,
        all_id_maps,
    )

    # -----------------------------------------------------
    # 출처 정보 추가
    # -----------------------------------------------------

    if episode_number is not None:

        for item in normalized_events:
            item["source_episode"] = episode_number

        for item in normalized_rules:
            item["source_episode"] = episode_number

        for item in normalized_times:
            item["source_episode"] = episode_number

        for item in normalized_locations:
            item["source_episode"] = episode_number

    # -----------------------------------------------------
    # 기존 통합 데이터와 병합
    # -----------------------------------------------------

    merged_characters = (
        existing["characters"]
        + normalized_new_characters
    )

    merged_events = (
        existing["events"]
        + normalized_events
    )

    merged_rules = (
        existing["worldview_rules"]
        + normalized_rules
    )

    merged_times = (
        existing["times"]
        + normalized_times
    )

    merged_locations = (
        existing["locations"]
        + normalized_locations
    )

    # -----------------------------------------------------
    # 저장
    # -----------------------------------------------------

    save_json(
        merged_characters,
        normalized_dir / "characters.json",
    )

    save_json(
        merged_events,
        normalized_dir / "events.json",
    )

    save_json(
        merged_rules,
        normalized_dir / "rules.json",
    )

    save_json(
        merged_times,
        normalized_dir / "times.json",
    )

    save_json(
        merged_locations,
        normalized_dir / "locations.json",
    )

    # -----------------------------------------------------
    # 호출자에게 처리 결과 반환
    # -----------------------------------------------------

    return {
        "characters_added": len(
            normalized_new_characters
        ),
        "events_added": len(
            normalized_events
        ),
        "rules_added": len(
            normalized_rules
        ),
        "times_added": len(
            normalized_times
        ),
        "locations_added": len(
            normalized_locations
        ),
        "id_maps": {
            "characters": character_map,
            "events": event_map,
            "rules": rule_map,
            "times": time_map,
            "locations": location_map,
        },
    }