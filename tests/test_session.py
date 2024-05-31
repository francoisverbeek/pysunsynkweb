"""Test the session module"""

import aiohttp
from aioresponses import aioresponses
import pytest
from pysunsynkweb.const import BASE_URL
from pysunsynkweb.exceptions import AuthenticationFailed
from pysunsynkweb.session import SunsynkwebSession
from yarl import URL


async def test_session_any_query_triggers_auth():
    """Check that a basic query triggers an auth request"""
    with aioresponses() as mocked:
        session = SunsynkwebSession(aiohttp.ClientSession(), "testuser", "testpassword")
        mocked.post(
            BASE_URL + "/oauth/token",
            status=200,
            payload={"code": 0, "msg": "Success", "data": {"access_token": "12345"}},
        )
        mocked.get(BASE_URL, payload={})
        resp = await session.get(BASE_URL)
        assert resp == {}
        req1, req2 = mocked.requests.keys()

        assert req1[0] == "POST"
        assert req2[0] == "GET"
    with aioresponses() as mocked:
        mocked.get(BASE_URL, payload={})
        assert session.bearer is not None
        resp = await session.get(BASE_URL)  # note: no POST call anymore, bearer is already set
        assert resp == {}


async def test_usession_failed_auth_retriggers_auth():
    """Check that if we get a 401 response we retry auth automatically, and the query as well"""
    with aioresponses() as mocked:
        session = SunsynkwebSession(aiohttp.ClientSession(), "testuser", "testpassword")
        mocked.post(
            BASE_URL + "/oauth/token",
            status=200,
            payload={"code": 0, "msg": "Success", "data": {"access_token": "12345"}},
        )
        mocked.get(BASE_URL, status=200, payload={"code": 401})
        mocked.post(
            BASE_URL + "/oauth/token",
            status=200,
            payload={"code": 0, "msg": "Success", "data": {"access_token": "12345"}},
        )
        mocked.get(BASE_URL, status=200, payload={})
        resp = await session.get(BASE_URL)
        assert resp == {}
        assert len(mocked.requests) == 2
        assert len(mocked.requests[("GET", URL(BASE_URL))]) == 2


async def test_usession_failed_auth_raises():
    """Check that if we fail auth, we raise and don't loop"""
    with aioresponses() as mocked:
        session = SunsynkwebSession(aiohttp.ClientSession(), "testuser", "testpassword")
        mocked.post(
            BASE_URL + "/oauth/token", status=200, payload={"code": 0, "msg": "Success", "data": {"invalid": "12345"}}
        )
        mocked.get(BASE_URL, status=200, payload={})
        with pytest.raises(AuthenticationFailed):
            await session.get(BASE_URL)
