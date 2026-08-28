'''임베딩 후 사건 연관 점수 산출'''

# ERS/calculator.py

from typing import Optional


Score = Optional[float]


# =========================================================
# 공통 가중 평균
# =========================================================

def weighted_average(
    items: list[tuple[Score, float]]
) -> Score:
    """
    None인 feature는 계산에서 제외하고
    사용 가능한 feature들의 가중치를 재정규화한다.

    예:
        semantic = 0.8, weight = 0.7
        action   = None, weight = 0.3

    결과:
        0.8

    None을 0점으로 취급하지 않는다.
    """

    valid_items = [
        (score, weight)
        for score, weight in items
        if score is not None
    ]

    if not valid_items:
        return None

    numerator = sum(
        score * weight
        for score, weight in valid_items
    )

    denominator = sum(
        weight
        for _, weight in valid_items
    )

    if denominator == 0:
        return None

    return numerator / denominator


# =========================================================
# Similarity
# =========================================================

def calculate_similarity(
    semantic: Score,
    action: Score,
) -> Score:
    """
    S_similarity =
        0.70 * S_semantic
        + 0.30 * S_action
    """

    return weighted_average([
        (semantic, 0.70),
        (action, 0.30),
    ])


# =========================================================
# Context
# =========================================================

def calculate_context(
    participant: Score,
    time: Score,
    location: Score,
    world: Score,
) -> Score:
    """
    S_context =
        0.45 * S_participant
        + 0.25 * S_time
        + 0.20 * S_location
        + 0.10 * S_world
    """

    return weighted_average([
        (participant, 0.45),
        (time, 0.25),
        (location, 0.20),
        (world, 0.10),
    ])


# =========================================================
# 최종 ERS
# =========================================================

def calculate_ers(
    semantic: Score,
    action: Score,
    causal: Score,
    participant: Score,
    time: Score,
    location: Score,
    world: Score,
) -> dict:
    """
    최종 사건 연관 점수 ERS를 계산한다.

    R(e_i, e_j) =
        0.30 * S_similarity
        + 0.45 * S_causal
        + 0.25 * S_context

    반환값에는 최종 점수뿐 아니라
    중간 계산 결과도 함께 포함한다.
    """

    similarity = calculate_similarity(
        semantic=semantic,
        action=action,
    )

    context = calculate_context(
        participant=participant,
        time=time,
        location=location,
        world=world,
    )

    relatedness = weighted_average([
        (similarity, 0.30),
        (causal, 0.45),
        (context, 0.25),
    ])

    return {
        "relatedness": relatedness,

        "similarity": similarity,
        "causal": causal,
        "context": context,

        "details": {
            "semantic": semantic,
            "action": action,
            "participant": participant,
            "time": time,
            "location": location,
            "world": world,
        },
    }