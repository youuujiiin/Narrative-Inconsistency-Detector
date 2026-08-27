"""전체 파이프라인 실행"""

from Project_scope_AI.ERS.embedding.bge_m3 import BGEM3Embedder
from Project_scope_AI.ERS.embedding.event_embedder import embed_events
from Project_scope_AI.ERS.io.json_handler import load_json, save_json


INPUT_PATH = "data/input/events.json"
OUTPUT_PATH = "data/embedded/event_embeddings.json"


def main():

    print("사건 JSON을 읽는 중...")

    events = load_json(INPUT_PATH)

    if not isinstance(events, list):
        raise ValueError(
            "events.json의 최상위 구조는 JSON 배열이어야 합니다."
        )

    print(f"사건 수: {len(events)}")

    print("BGE-M3 모델을 불러오는 중...")

    embedder = BGEM3Embedder()

    print("사건 임베딩 시작...")

    embedded_events = embed_events(
        events,
        embedder,
    )

    print("임베딩 결과 저장 중...")

    save_json(
        embedded_events,
        OUTPUT_PATH,
    )

    print(
        f"완료: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()