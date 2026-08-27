# API 호출
import os
from pathlib import Path

from anthropic import Anthropic


MODEL_NAME = "claude-haiku-4-5"
DEFAULT_MAX_TOKENS = 8192


def read_text_file(file_path: str | Path) -> str:
    """
    UTF-8 텍스트 파일을 읽어서 문자열로 반환한다.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"파일을 찾을 수 없습니다: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return file.read()


def create_client() -> Anthropic:
    """
    환경 변수에서 Anthropic API Key를 읽어
    Anthropic client를 생성한다.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY 환경 변수가 설정되어 있지 않습니다."
        )

    return Anthropic(
        api_key=api_key,
    )


def call_claude(
    source_path: str | Path,
    prompt_path: str | Path,
    extra_context: str | None = None,
    model: str = MODEL_NAME,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """
    원문 파일과 프롬프트 파일을 읽은 뒤
    Claude API를 호출하고 응답 텍스트를 반환한다.

    Parameters
    ----------
    source_path:
        분석할 원문 파일 경로

    prompt_path:
        사용할 프롬프트 파일 경로

    extra_context:
        ERS Top-K 결과 등 추가로 전달할 정보.
        1차 분석에서는 None으로 사용할 수 있다.

    model:
        사용할 Claude 모델

    max_tokens:
        최대 출력 토큰 수
    """

    source_text = read_text_file(source_path)
    prompt_text = read_text_file(prompt_path)

    user_content = source_text

    if extra_context:
        user_content += (
            "\n\n"
            "===== 추가 참고 정보 =====\n"
            f"{extra_context}"
        )

    client = create_client()

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,

        # 프롬프트 파일의 내용은 system prompt로 사용
        system=prompt_text,

        # 원문과 추가 context는 user message로 전달
        messages=[
            {
                "role": "user",
                "content": user_content,
            }
        ],
    )

    text_blocks = [
        block.text
        for block in response.content
        if block.type == "text"
    ]

    return "\n".join(text_blocks)