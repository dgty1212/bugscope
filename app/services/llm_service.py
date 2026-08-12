from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.core.config import get_settings
from app.prompts.debug_analysis import SYSTEM_PROMPT
from app.schemas.analysis import DebugAnalysisResult

settings = get_settings()

client = OpenAI(
    api_key=settings.openai_api_key,
)


class LLMAnalysisError(Exception):
    """LLM 디버깅 분석 실패."""


def analyze_debug_context(
    user_prompt: str,
) -> DebugAnalysisResult:
    """검색된 코드와 오류 로그를 LLM으로 분석한다."""

    schema = DebugAnalysisResult.model_json_schema()

    try:
        response = client.responses.create(
            model=settings.openai_analysis_model,
            instructions=SYSTEM_PROMPT,
            input=user_prompt,
            reasoning={
                "effort": "low",
            },
            text={
                "format": {
                    "type": "json_schema",
                    "name": "debug_analysis_result",
                    "schema": schema,
                    "strict": True,
                }
            },
        )

    except OpenAIError as error:
        raise LLMAnalysisError(
            "OpenAI API 호출에 실패했습니다."
        ) from error

    if not response.output_text:
        raise LLMAnalysisError(
            "LLM이 분석 결과를 반환하지 않았습니다."
        )

    try:
        return DebugAnalysisResult.model_validate_json(
            response.output_text
        )

    except ValidationError as error:
        raise LLMAnalysisError(
            "LLM 응답을 분석 결과 스키마로 변환할 수 없습니다."
        ) from error