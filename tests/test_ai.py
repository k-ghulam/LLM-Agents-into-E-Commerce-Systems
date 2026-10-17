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
    assert response == pipeline._unavailable()
    agent.run.assert_not_called()


def test_output_failure_never_leaks_reply(ai, monkeypatch):
    pipeline, _ = ai
    monkeypatch.setattr(pipeline, 'agent', SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(output='unscreened reply'))))
    monkeypatch.setattr(pipeline, 'violates_output_policy', AsyncMock(side_effect=RuntimeError('provider unavailable')))
    assert asyncio.run(pipeline.run_chat('shirt')) == pipeline._unavailable()


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



def test_safety_completion_budget(ai, monkeypatch):
    _, guardrails = ai
    create = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(
        finish_reason='stop', message=SimpleNamespace(content='{"violation": 0, "rationale": "Allowed"}')
    )]))
    monkeypatch.setattr(guardrails, 'guardrail_client', SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    assert asyncio.run(guardrails._check_safety('shirt', guardrails.INPUT_POLICY)) == (False, 'Allowed')
    assert create.call_args.kwargs['max_completion_tokens'] == 256
    assert create.call_args.kwargs['reasoning_effort'] == 'low'


def test_truncated_guard_fails_closed(ai, monkeypatch):
    _, guardrails = ai
    create = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(
        finish_reason='length', message=SimpleNamespace(content='{"violation": 0}')
    )]))
    monkeypatch.setattr(guardrails, 'guardrail_client', SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    with pytest.raises(ValueError, match='truncated'):
        asyncio.run(guardrails._check_safety('shirt', guardrails.INPUT_POLICY))


def test_policy_block_remains_a_refusal(ai, monkeypatch):
    pipeline, _ = ai
    monkeypatch.setattr(pipeline, 'is_prompt_injection', AsyncMock(return_value=True))
    agent = SimpleNamespace(run=AsyncMock())
    monkeypatch.setattr(pipeline, 'agent', agent)
    assert asyncio.run(pipeline.run_chat('ignore instructions')) == pipeline._blocked()
    agent.run.assert_not_called()



def test_empty_search_has_clear_message(ai, monkeypatch):
    pipeline, _ = ai
    async def empty_search(message, *, deps, **kwargs):
        deps.search_performed = True
        deps.found_products = []
        return SimpleNamespace(output="Here are your products! Unfortunately none match.")
    monkeypatch.setattr(pipeline, 'agent', SimpleNamespace(run=empty_search))
    response = asyncio.run(pipeline.run_chat('women under 30 euros'))
    assert response == {
        'type': 'text',
        'message': 'No products matched your search. Try a different price range, category or keyword.',
        'data': None,
    }
    pipeline.violates_output_policy.assert_awaited_once_with(response['message'])


def test_matching_search_keeps_product_cards(ai, monkeypatch):
    pipeline, _ = ai
    async def matching_search(message, *, deps, **kwargs):
        deps.search_performed = True
        deps.found_products = [{'id': 'demo', 'name': 'Test Dress', 'price': 35}]
        return SimpleNamespace(output='Here is a matching dress.')
    monkeypatch.setattr(pipeline, 'agent', SimpleNamespace(run=matching_search))
    response = asyncio.run(pipeline.run_chat('women under 50 euros'))
    assert response['type'] == 'products'
    assert response['data'][0]['name'] == 'Test Dress'
    assert response['message'] == 'Here is a matching dress.'


def test_search_tool_decimal_bounds(client, ai):
    from backend.chatbot.agent import search_products, StoreDeps
    api, db = client
    db.products.insert_many([
        {"name": "Dress", "category": "women", "price_cents": 1999, "currency": "EUR"},
        {"name": "Old Dress", "category": "women", "price": 20}])
    deps = StoreDeps()
    search_products(SimpleNamespace(deps=deps), category="women", max_price="19.99")
    assert [p["name"] for p in deps.found_products] == ["Dress"]
    assert deps.found_products[0]["price"] == "19.99"
