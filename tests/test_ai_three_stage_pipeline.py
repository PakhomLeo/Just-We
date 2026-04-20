"""Tests for the three-stage AI analysis pipeline."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.main import app
from app.models.user import UserRole
from app.services.ai_service import AIAnalysisException, AIService, StrictJSONParseError


def llm_response(payload):
    return {"choices": [{"message": {"content": payload}}]}


def test_strict_json_parser_accepts_json_and_markdown_fence():
    service = AIService()

    assert service.parse_json_response(llm_response('{"summary":"ok"}')) == {"summary": "ok"}
    assert service.parse_json_response(llm_response('```json\n{"summary":"ok"}\n```')) == {"summary": "ok"}

    with pytest.raises(StrictJSONParseError):
        service.parse_json_response(llm_response("前缀 {\"summary\":\"bad\"}"))


@pytest.mark.asyncio
async def test_type_judgment_retries_until_yes_or_no(monkeypatch):
    service = AIService()
    calls = [
        llm_response(json.dumps({"target_match": "也许"}, ensure_ascii=False)),
        llm_response(json.dumps({"target_match": "是", "reason": "符合"}, ensure_ascii=False)),
    ]

    async def fake_call_llm(**kwargs):
        return calls.pop(0)

    monkeypatch.setattr(service, "_call_llm", fake_call_llm)

    result = await service.judge_target_type({"summary": "AI"}, {"summary": "diagram"}, "AI 产品动态")

    assert result["target_match"] == "是"
    assert result["target_type"] == "AI 产品动态"
    assert calls == []


@pytest.mark.asyncio
async def test_type_judgment_fails_after_invalid_retry(monkeypatch):
    service = AIService()

    async def fake_call_llm(**kwargs):
        return llm_response(json.dumps({"target_match": "maybe"}, ensure_ascii=False))

    monkeypatch.setattr(service, "_call_llm", fake_call_llm)

    with pytest.raises(AIAnalysisException):
        await service.judge_target_type({"summary": "x"}, {}, "目标类型")


@pytest.mark.asyncio
async def test_article_pipeline_merges_text_image_and_type(monkeypatch):
    service = AIService()
    monkeypatch.setattr(service, "_is_api_configured", lambda config: True)

    async def fake_call_json_stage(**kwargs):
        prompt = kwargs["prompt"]
        if "target_match" in prompt:
            return {"target_match": "不是", "reason": "不符合", "confidence": 0.8}
        if kwargs.get("image_paths"):
            return {"summary": "图片包含产品截图", "images": [{"label": "screenshot"}]}
        return {"summary": "文字介绍体育赛事", "keywords": ["体育"]}

    monkeypatch.setattr(service, "_call_json_stage", fake_call_json_stage)

    result = await service.analyze_article_pipeline("正文内容", ["missing-image.jpg"])

    assert result["status"] == "success"
    assert result["ratio"] == 0.0
    assert result["ai_target_match"] == "不是"
    assert result["ai_text_analysis"]["summary"] == "文字介绍体育赛事"
    assert result["ai_image_analysis"]["summary"] == "图片包含产品截图"


@pytest.mark.asyncio
async def test_image_analysis_skips_without_images():
    service = AIService()

    result = await service.analyze_images([])

    assert result == {"skipped": True, "reason": "no_images", "images": []}


@pytest.mark.asyncio
async def test_image_analysis_skips_when_image_api_is_not_configured():
    service = AIService()
    service.config = type(
        "Config",
        (),
        {
            "enabled": True,
            "image_enabled": True,
            "image_api_url": "https://api.example.com/v1/chat/completions",
            "image_api_key": "your-api-key",
            "image_model": "gpt-4o",
            "timeout_seconds": 60,
            "image_analysis_prompt": "image",
        },
    )()

    result = await service.analyze_images(["some-image.jpg"])

    assert result == {"skipped": True, "reason": "image_ai_not_configured", "images": []}


def test_deepseek_base_url_is_normalized_to_chat_completions_endpoint():
    service = AIService()

    assert service._normalize_chat_completions_url("https://api.deepseek.com") == (
        "https://api.deepseek.com/chat/completions"
    )
    assert service._normalize_chat_completions_url("https://api.deepseek.com/v1") == (
        "https://api.deepseek.com/v1/chat/completions"
    )
    assert service._normalize_chat_completions_url("https://api.deepseek.com/chat/completions") == (
        "https://api.deepseek.com/chat/completions"
    )


def test_ark_image_sample_url_is_normalized_to_chat_completions_endpoint():
    service = AIService()

    assert service._normalize_chat_completions_url(
        "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg",
        "doubao-seed-2-0-lite-260215",
    ) == "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    assert service._normalize_chat_completions_url(
        "https://ark.cn-beijing.volces.com/api/v3",
        "doubao-seed-2-0-lite-260215",
    ) == "https://ark.cn-beijing.volces.com/api/v3/chat/completions"


def test_http_image_urls_are_passed_through_for_vision_models():
    service = AIService()

    assert service._image_to_request_image_url("https://mmbiz.qpic.cn/example.png") == (
        "https://mmbiz.qpic.cn/example.png"
    )


@pytest.mark.asyncio
async def test_ai_config_api_persists_three_stage_fields(mock_user):
    mock_user.role = UserRole.ADMIN

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            "/api/system/ai-config",
            json={
                "api_url": "https://api.example.com/v1/chat/completions",
                "api_key": "text-key",
                "model": "text-model",
                "prompt_template": "legacy {{content}}",
                "enabled": True,
                "text_api_url": "https://text.example.com/v1/chat/completions",
                "text_api_key": "text-key",
                "text_model": "text-model",
                "text_enabled": True,
                "image_api_url": "https://image.example.com/v1/chat/completions",
                "image_api_key": "image-key",
                "image_model": "image-model",
                "image_enabled": True,
                "text_analysis_prompt": "text {{content}}",
                "image_analysis_prompt": "image",
                "type_judgment_prompt": "type {{target_type}} {{text_analysis}} {{image_analysis}}",
                "target_article_type": "AI 产品动态",
                "timeout_seconds": 45,
            },
        )
        get_response = await client.get("/api/system/ai-config")
    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["target_article_type"] == "AI 产品动态"
    assert get_response.status_code == 200
    assert get_response.json()["image_model"] == "image-model"
