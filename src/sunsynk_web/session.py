"""A session object

Maintaining the authentication with the sunsynk api and
wrapping repetitive things
"""

import logging
import pprint

import aiohttp

from .const import BASE_HEADERS, BASE_URL
from .exceptions import AuthenticationFailed

_LOGGER = logging.getLogger(__name__)


class SunsynkwebSession:
    """the main entry point to sunsynk api.

    Maintains http headers,
    authentication token, etc.
    """

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        """Pass an aiohttp client session and authentication items"""
        self.session = session
        self.bearer = None
        self.username = username
        self.password = password

    async def get(self, *args, **kwargs):
        """Run a GET query against the sunsynk api"""
        if self.bearer is None:
            await self._get_bearer_token()
        headers = BASE_HEADERS.copy()
        headers.update({"Authorization": f"Bearer{self.bearer}"})
        kwargs["headers"] = headers
        result = await self.session.get(*args, **kwargs)
        result = await result.json()
        if result.get("msg") != "Success" and result.get("code") == 401:
            # expired token
            await self._get_bearer_token()
            result = await self.get(*args, **kwargs)
        return result

    async def _get_bearer_token(self):
        """Get the bearer token for the sunsynk api."""
        params = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
            "client_id": "csp-web",
            "source": "sunsynk",
            "areaCode": "sunsynk",
        }
        returned = await self.session.post(BASE_URL + "/oauth/token", json=params, headers=BASE_HEADERS)

        returned = await returned.json()
        _LOGGER.debug("authentication attempt returned %s", pprint.pformat(returned))
        # returned data looks like the below
        # {
        #     "code": 0,
        #     "msg": "Success",
        #     "data": {
        #         "access_token": "VALUE",
        #         "token_type": "bearer",
        #         "refresh_token": "VALUE",
        #         "expires_in": 604799,
        #         "scope": "all",
        #     },
        #     "success": True,
        # }
        try:
            self.bearer = returned["data"]["access_token"]
        except KeyError as exc:
            raise AuthenticationFailed from exc
