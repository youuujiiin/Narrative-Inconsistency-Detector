'''캐릭터/세계관 룰 split&normalization'''
import re
from copy import deepcopy


# =========================================================
# 공통 ID 처리
# =========================================================

def extract_id_number(identifier: str, prefix: str) -> int:
    """
    CHAR_001 -> 1
    RULE_012 -> 12
    """

    pattern = rf"^{re.escape(prefix)}_(\d+)$"
    match = re.match(pattern, identifier)

    if not match:
        raise ValueError(
            f"잘못된 ID 형식입니다: {identifier}"
        )

    return int(match.group(1))


def get_next_id_number(
    items: list[dict],
    id_field: str,
    prefix: str,
) -> int:
    """
    기존 통합 JSON에서 가장 큰 ID를 찾아
    다음에 사용할 번호를 반환한다.

    예:
        CHAR_001
        CHAR_002
        CHAR_005

    -> 6
    """

    max_number = 0

    for item in items:
        identifier = item.get(id_field)

        if not identifier:
            continue

        try:
            number = extract_id_number(
                identifier,
                prefix,
            )
        except ValueError:
            continue

        max_number = max(max_number, number)

    return max_number + 1


# =========================================================
# 캐릭터 이름 / aliases 처리
# =========================================================

def normalize_character_text(value: str | None) -> str:
    """
    캐릭터 이름 비교용 문자열 정규화.

    현재는:
    - 앞뒤 공백 제거
    - 소문자 변환

    만 수행한다.
    """

    if not value:
        return ""

    return value.strip().lower()


def get_character_names(character: dict) -> set[str]:
    """
    캐릭터의 name + aliases를 하나의 집합으로 만든다.

    예:

    {
        "name": "알파",
        "aliases": ["플레이어", "α-0760"]
    }

    -> {"알파", "플레이어", "α-0760"}
    """

    names = set()

    name = character.get("name")

    if name:
        normalized_name = normalize_character_text(name)

        if normalized_name:
            names.add(normalized_name)

    aliases = character.get("aliases", [])

    if isinstance(aliases, list):
        for alias in aliases:
            normalized_alias = normalize_character_text(alias)

            if normalized_alias:
                names.add(normalized_alias)

    return names


def find_existing_character(
    new_character: dict,
    existing_characters: list[dict],
) -> dict | None:
    """
    새 캐릭터의 name / aliases와
    기존 캐릭터의 name / aliases가 하나라도 겹치면
    동일 캐릭터로 판단한다.

    현재는 exact match 방식이다.
    """

    new_names = get_character_names(new_character)

    if not new_names:
        return None

    for existing_character in existing_characters:
        existing_names = get_character_names(
            existing_character
        )

        if new_names & existing_names:
            return existing_character

    return None


def merge_aliases(
    existing_character: dict,
    new_character: dict,
) -> None:
    """
    기존 캐릭터에 새롭게 발견된 이름 / alias를 병합한다.

    기존 캐릭터의 대표 name은 변경하지 않는다.
    """

    existing_name = normalize_character_text(
        existing_character.get("name")
    )

    existing_aliases = existing_character.get(
        "aliases",
        [],
    )

    if not isinstance(existing_aliases, list):
        existing_aliases = []

    # 실제 저장용 alias
    alias_map = {
        normalize_character_text(alias): alias
        for alias in existing_aliases
        if normalize_character_text(alias)
    }

    # 새 캐릭터의 name도 기존 대표 name과 다르면
    # alias 후보로 취급
    new_name = new_character.get("name")

    if new_name:
        normalized_new_name = normalize_character_text(
            new_name
        )

        if (
            normalized_new_name
            and normalized_new_name != existing_name
        ):
            alias_map.setdefault(
                normalized_new_name,
                new_name.strip(),
            )

    # 새 aliases 병합
    new_aliases = new_character.get(
        "aliases",
        [],
    )

    if isinstance(new_aliases, list):
        for alias in new_aliases:
            normalized_alias = normalize_character_text(
                alias
            )

            if (
                normalized_alias
                and normalized_alias != existing_name
            ):
                alias_map.setdefault(
                    normalized_alias,
                    alias.strip(),
                )

    existing_character["aliases"] = list(
        alias_map.values()
    )


def add_source_episode(
    character: dict,
    episode_number: int,
) -> None:
    """
    캐릭터가 어느 화에서 인식되었는지 기록한다.

    캐릭터는 여러 화에서 반복 등장할 수 있으므로
    source_episodes 배열을 사용한다.
    """

    episodes = character.get(
        "source_episodes",
        [],
    )

    if not isinstance(episodes, list):
        episodes = []

    if episode_number not in episodes:
        episodes.append(episode_number)

    episodes.sort()

    character["source_episodes"] = episodes


# =========================================================
# 캐릭터 처리
# =========================================================

def handle_characters(
    new_characters: list[dict],
    existing_characters: list[dict],
    episode_number: int,
) -> dict:
    """
    신규 화에서 추출된 캐릭터를 기존 characters와 비교한다.

    규칙:
    1. name / aliases가 기존 캐릭터와 겹치면 동일 인물
    2. 동일 인물이라면 기존 ID 유지
    3. 새 alias는 기존 캐릭터에 병합
    4. 신규 인물이라면 새 CHAR ID 부여
    5. local CHAR ID -> global CHAR ID mapping 반환

    반환 예:

    {
        "characters": [...전체 캐릭터...],

        "id_map": {
            "CHAR_001": "CHAR_003",
            "CHAR_002": "CHAR_008"
        },

        "new_character_ids": [
            "CHAR_008"
        ]
    }
    """

    characters = deepcopy(existing_characters)

    next_number = get_next_id_number(
        characters,
        id_field="character_id",
        prefix="CHAR",
    )

    id_map: dict[str, str] = {}

    new_character_ids: list[str] = []

    for new_character in new_characters:

        local_id = new_character.get(
            "character_id"
        )

        if not local_id:
            raise ValueError(
                "character_id가 없는 캐릭터가 있습니다."
            )

        # -----------------------------------------
        # 기존 캐릭터 검색
        # -----------------------------------------

        existing_character = find_existing_character(
            new_character,
            characters,
        )

        if existing_character is not None:

            global_id = existing_character[
                "character_id"
            ]

            id_map[local_id] = global_id

            # 새롭게 발견된 aliases 병합
            merge_aliases(
                existing_character,
                new_character,
            )

            # 이번 화에서도 등장했다는 정보 추가
            add_source_episode(
                existing_character,
                episode_number,
            )

            continue

        # -----------------------------------------
        # 신규 캐릭터
        # -----------------------------------------

        global_id = (
            f"CHAR_{next_number:03d}"
        )

        next_number += 1

        character = deepcopy(
            new_character
        )

        character["character_id"] = global_id

        # aliases가 없다면 빈 배열 생성
        if not isinstance(
            character.get("aliases"),
            list,
        ):
            character["aliases"] = []

        character["source_episodes"] = [
            episode_number
        ]

        characters.append(character)

        id_map[local_id] = global_id

        new_character_ids.append(
            global_id
        )

    return {
        "characters": characters,
        "id_map": id_map,
        "new_character_ids": new_character_ids,
    }


# =========================================================
# 세계관 Rule 처리
# =========================================================

def handle_rules(
    new_rules: list[dict],
    existing_rules: list[dict],
    episode_number: int,
) -> dict:
    """
    신규 화의 worldview rule을 기존 rules 뒤에 추가한다.

    현재 단계에서는:
    - 동일 rule 여부 판단 안 함
    - 무조건 신규 rule로 등록
    - global RULE ID 순차 부여
    - source_episode 기록
    - 원래 LLM이 생성한 local ID도 source_local_id로 보존

    반환 예:

    {
        "rules": [...전체 rule...],

        "id_map": {
            "RULE_001": "RULE_025",
            "RULE_002": "RULE_026"
        },

        "new_rule_ids": [
            "RULE_025",
            "RULE_026"
        ]
    }
    """

    rules = deepcopy(existing_rules)

    next_number = get_next_id_number(
        rules,
        id_field="rule_id",
        prefix="RULE",
    )

    id_map: dict[str, str] = {}

    new_rule_ids: list[str] = []

    for new_rule in new_rules:

        local_id = new_rule.get(
            "rule_id"
        )

        if not local_id:
            raise ValueError(
                "rule_id가 없는 세계관 규칙이 있습니다."
            )

        global_id = (
            f"RULE_{next_number:03d}"
        )

        next_number += 1

        rule = deepcopy(
            new_rule
        )

        rule["rule_id"] = global_id

        # 같은 화에서 나온 규칙인지 추적
        rule["source_episode"] = (
            episode_number
        )

        # LLM 원본 ID도 보존
        rule["source_local_id"] = (
            local_id
        )

        rules.append(rule)

        id_map[local_id] = global_id

        new_rule_ids.append(
            global_id
        )

    return {
        "rules": rules,
        "id_map": id_map,
        "new_rule_ids": new_rule_ids,
    }


# =========================================================
# id_handler 통합 진입점
# =========================================================

def handle_ids(
    new_characters: list[dict],
    new_rules: list[dict],
    existing_characters: list[dict],
    existing_rules: list[dict],
    episode_number: int,
) -> dict:
    """
    Character + Worldview Rule ID 처리를 한 번에 수행한다.

    split_idmanager 등 다른 모듈에서는
    반환된 character_id_map / rule_id_map을 이용해
    Event 내부 참조 ID를 변경할 수 있다.
    """

    character_result = handle_characters(
        new_characters=new_characters,
        existing_characters=existing_characters,
        episode_number=episode_number,
    )

    rule_result = handle_rules(
        new_rules=new_rules,
        existing_rules=existing_rules,
        episode_number=episode_number,
    )

    return {
        "characters": character_result[
            "characters"
        ],
        "rules": rule_result[
            "rules"
        ],

        "character_id_map": character_result[
            "id_map"
        ],
        "rule_id_map": rule_result[
            "id_map"
        ],

        "new_character_ids": character_result[
            "new_character_ids"
        ],
        "new_rule_ids": rule_result[
            "new_rule_ids"
        ],
    }
