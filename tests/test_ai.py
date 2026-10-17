import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest


@pytest.fixture
def ai(monkeypatch):
    # Import real AI modules without provider requests. Remove this runner's proxy
    # settings because their optional SOCKS transport is unrelated to the app.
    for key in ('ALL_PROXY', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('GROQ_API_KEY', 'test-key-not-a-real-secret')
    from backend.config import settings
    monkeypatch.setattr(settings, 'groq_api_key', 'test-key-not-a-real-secret')
    pipeline = importlib.import_module('backend.chatbot.pipeline')
    guardrails = importlib.import_module('backend.chatbot.guardrails')
    monkeypatch.setattr(pipeline, 'is_prompt_injection', AsyncMock(return_value=False))
    monkeypatch.setattr(pipeline, 'violates_content_policy', AsyncMock(return_value=False))
    monkeypatch.setattr(pipeline, 'violates_output_policy', AsyncMock(return_value=False))
    return pipeline, guardrails


def test_guard_failure_never_runs_agent(ai, monkeypatch):
    pipeline, _ = ai
    monkeypatch.setattr(pipeline, 'is_prompt_injection', AsyncMock(side_effect=RuntimeError('provider unavailable')))
    agent = SimpleNamespace(run=AsyncMock())
    monkeypatch.setattr(pipeline, 'agent', agent)
    response = asyncio.run(pipeline.run_chat('show shirts'))
    assert response == pipeline._blocked()
    agent.run.assert_not_called()


def test_output_failure_never_leaks_reply(ai, monkeypatch):
    pipeline, _ = ai
    monkeypatch.setattr(pipeline, 'agent', SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(output='unscreened reply'))))
    monkeypatch.setattr(pipeline, 'violates_output_policy', AsyncMock(side_effect=RuntimeError('provider unavailable')))
    assert asyncio.run(pipeline.run_chat('shirt')) == pipeline._blocked()


@pytest.mark.parametrize('raw', ['garbage', '{}', '{"violation": "0"}', '{"violation": 2}', '[]'])
def test_malformed_guard_fails_closed(ai, monkeypatch, raw):
    _, guardrails = ai
    create = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw))]))
    monkeypatch.setattr(guardrails, 'guardrail_client', SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    with pytest.raises(ValueError): asyncio.run(guardrails._check_safety('shirt', 'policy'))


@pytest.mark.parametrize('raw', ['nan', '-1', '2', 'unparseable'])
def test_invalid_injection_score_rejected(ai, monkeypatch, raw):
    _, guardrails = ai
    create = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw))]))
    monkeypatch.setattr(guardrails, 'guardrail_client', SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    with pytest.raises(ValueError): asyncio.run(guardrails.is_prompt_injection('shirt'))


def test_normal_chat_and_independent_run_state(ai, monkeypatch):
    pipeline, _ = ai
    monkeypatch.setattr(pipeline, 'agent', SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(output='Hello'))))
    assert asyncio.run(pipeline.run_chat('Hi')) == {'type': 'text', 'message': 'Hello', 'data': None}
    first, second = pipeline.StoreDeps(), pipeline.StoreDeps()
    first.found_products.append({'name': 'Shirt'})
    assert second.found_products == []
