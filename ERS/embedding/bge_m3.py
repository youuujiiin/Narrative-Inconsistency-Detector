"""실제 임베딩 모델. 이 코드는 BGE-M3 사용."""
from sentence_transformers import SentenceTransformer

from .base import BaseEmbedder


class BGEM3Embedder(BaseEmbedder):

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str | None = None,
    ):
        self.model = SentenceTransformer(
            model_name,
            device=device,
        )

    def embed(self, text: str) -> list[float]:
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True,
        )

        return embeddings.tolist()