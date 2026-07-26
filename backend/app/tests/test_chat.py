import uuid

from app.api.v1.chat import _report_cache_key


def test_report_cache_key_is_stable_for_identical_query():
    user_id = uuid.uuid4()
    assert _report_cache_key(user_id, "What is the price of Bitcoin?") == _report_cache_key(
        user_id, "What is the price of Bitcoin?"
    )


def test_report_cache_key_normalizes_case_and_whitespace():
    user_id = uuid.uuid4()
    assert _report_cache_key(user_id, "  Bitcoin PRICE  ") == _report_cache_key(user_id, "bitcoin price")


def test_report_cache_key_differs_per_user():
    query = "What is the price of Bitcoin?"
    assert _report_cache_key(uuid.uuid4(), query) != _report_cache_key(uuid.uuid4(), query)


def test_report_cache_key_differs_for_different_queries():
    user_id = uuid.uuid4()
    assert _report_cache_key(user_id, "question one") != _report_cache_key(user_id, "question two")
