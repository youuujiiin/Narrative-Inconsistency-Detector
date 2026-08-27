"""임베딩 모델 공통 인터페이스"""
from abc import ABC, abstractmethod


class BaseEmbedder(ABC):

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """문자열 하나를 임베딩 벡터로 변환한다."""
        raise NotImplementedError

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """여러 문자열을 한 번에 임베딩한다."""
        raise NotImplementedError