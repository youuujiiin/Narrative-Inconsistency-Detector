"""정규화된 전체 사건 JSON을 BGE-M3로 임베딩한다."""

from pathlib import Path

from ERS.embedding.bge_m3 import BGEM3Embedder
from ERS.embedding.event_embedder import embed_events
from ERS.io.json_handler import load_json, save_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "Data" / "normalized" / "events.json"
OUTPUT_PATH = PROJECT_ROOT / "Data" / "embedded" / "event_embeddings.json"


def main() -> None:
    print("사건 JSON을 읽는 중...")
    events = load_json(INPUT_PATH)

    if not isinstance(events, list):
        raise ValueError("events.json의 최상위 구조는 JSON 배열이어야 합니다.")

    print(f"사건 수: {len(events)}")
    print("BGE-M3 모델을 불러오는 중...")

    embedder = BGEM3Embedder()

    print("사건 임베딩 시작...")
    embedded_events = embed_events(events, embedder)

    output = {
        "model": "BAAI/bge-m3",
        "embedding_fields": ["title", "summary", "cause", "result"],
        "events": embedded_events,
    }

    print("임베딩 결과 저장 중...")
    save_json(output, OUTPUT_PATH)
    print(f"완료: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
