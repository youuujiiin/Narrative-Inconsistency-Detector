"""사건 임베더"""

from .base import BaseEmbedder


EMBEDDING_FIELDS = (
    "title",
    "summary",
    "cause",
    "result",
)


def embed_events(
    events: list[dict],
    embedder: BaseEm"""이벤트 임베더"""

from .base import BaseEmbedder


EMBEDDING_FIELDS = (
    "title",
    "summary",
    "cause",
    "result",
)


def embed_events(
    events: list[dict],
    embedder: BaseEmbedder,
) -> list[dict]:

    results = []

    for event in events:
        result = {
            "event_id": event.get("event_id"),
        }

        for field in EMBEDDING_FIELDS:
            result[f"{field}_embedding"] = None

        results.append(result)

    # 필드별로 batch embedding
    for field in EMBEDDING_FIELDS:

        texts = []
        event_indexes = []

        for index, event in enumerate(events):
            text = event.get(field)

            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
                event_indexes.append(index)

        if not texts:
            continue

        embeddings = embedder.embed_batch(texts)

        for index, embedding in zip(
            event_indexes,
            embeddings,
        ):
            results[index][f"{field}_embedding"] = embedding

    return resultsbedder,
) -> list[dict]:

    results = []

    for event in events:
        result = {
            "event_id": event.get("event_id"),
        }

        for field in EMBEDDING_FIELDS:
            result[f"{field}_embedding"] = None

        results.append(result)

    # 필드별로 batch embedding
    for field in EMBEDDING_FIELDS:

        texts = []
        event_indexes = []

        for index, event in enumerate(events):
            text = event.get(field)

            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
                event_indexes.append(index)

        if not texts:
            continue

        embeddings = embedder.embed_batch(texts)

        for index, embedding in zip(
            event_indexes,
            embeddings,
        ):
            results[index][f"{field}_embedding"] = embedding

    return results