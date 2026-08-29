"""Claude API 공통 호출 클라이언트."""

import json
import os
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv


# 프로젝트 루트의 .env를 로컬 개발 환경에서 읽는다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

MODEL_NAME = "claude-haiku-4-5"
DEFAULT_MAX_TOKENS = 8192


def read_text_file(file_path: str | Path) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    with path.open("r", encoding="utf-8") as file:
        return file.read()


def create_client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY가 설정되어 있지 않습니다. "
            "프로젝트 루트의 .env 또는 서버 환경변수를 확인하세요."
        )

    return Anthropic(api_key=api_key)


def serialize_context(extra_context: Any) -> str:
    """ERS Top-K의 list/dict 등을 Claude에 전달할 JSON 문자열로 변환한다."""
    if isinstance(extra_context, str):
        return extra_context

    return json.dumps(extra_context, ensure_ascii=False, indent=2)


def call_claude(
    source_path: str | Path,
    prompt_path: str | Path,
    extra_context: Any | None = None,
    model: str = MODEL_NAME,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """프롬프트와 원문을 읽어 Claude를 호출하고 텍스트 응답을 반환한다."""
    source_text = read_text_file(source_path)
    prompt_text = read_text_file(prompt_path)

    user_content = source_text
    if extra_context is not None:
        user_content += (
            "\n\n===== 추가 참고 정보 =====\n"
            + serialize_context(extra_context)
        )

    response = create_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=prompt_text,
        messages=[{"role": "user", "content": user_content}],
    )

    return "\n".join(
        block.text
        for block in response.content
        if block.type == "text"
    )
