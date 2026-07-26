import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import get_optional_checker_chat_id
from app.core.security import create_access_token, generate_api_key


def _db_with_result(scalar_value):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar_value)
    db.execute = AsyncMock(return_value=result)
    return db


async def test_returns_none_with_no_credentials_at_all():
    db = _db_with_result(None)
    result = await get_optional_checker_chat_id(credentials=None, api_key=None, db=db)
    assert result is None
    db.execute.assert_not_called()


async def test_returns_none_for_garbage_jwt_without_raising():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-real-token")
    db = _db_with_result(None)
    result = await get_optional_checker_chat_id(credentials=creds, api_key=None, db=db)
    assert result is None


async def test_returns_none_when_valid_jwt_has_no_telegram_link():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    db = _db_with_result(None)  # no TelegramLink row found

    result = await get_optional_checker_chat_id(credentials=creds, api_key=None, db=db)

    assert result is None


async def test_returns_chat_id_when_valid_jwt_has_telegram_link():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    link = MagicMock(telegram_chat_id="55555")
    db = _db_with_result(link)

    result = await get_optional_checker_chat_id(credentials=creds, api_key=None, db=db)

    assert result == "55555"


async def test_returns_none_for_invalid_api_key():
    db = _db_with_result(None)  # ApiKey lookup misses
    result = await get_optional_checker_chat_id(credentials=None, api_key="toc_garbage", db=db)
    assert result is None


async def test_returns_chat_id_for_valid_api_key_owner_with_link():
    _, key_hash, _ = generate_api_key()
    user_id = uuid.uuid4()

    api_key_record = MagicMock(created_by_user_id=user_id, revoked_at=None, key_hash=key_hash)
    link = MagicMock(telegram_chat_id="99999")

    db = AsyncMock()
    api_key_result = MagicMock()
    api_key_result.scalar_one_or_none = MagicMock(return_value=api_key_record)
    link_result = MagicMock()
    link_result.scalar_one_or_none = MagicMock(return_value=link)
    db.execute = AsyncMock(side_effect=[api_key_result, link_result])

    result = await get_optional_checker_chat_id(credentials=None, api_key="toc_whatever", db=db)

    assert result == "99999"
