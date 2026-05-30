import base64
import hashlib
import time

import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding


# This client is sourced from https://github.com/jamesridgway/sunsynk-api-client/tree/main


class InvalidCredentialsException(Exception):
    def __init__(self):
        super().__init__("Invalid username or password")


class SunsynkClient:
    _SOURCE = "sunsynk"
    _CLIENT_ID = "csp-web"

    @classmethod
    async def create(cls, username: str, password: str, base_url: str = None):
        self = SunsynkClient(username, password, base_url)
        return await self.login()

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = None,
        session: aiohttp.ClientSession = None,
    ):
        self.base_url = "https://api.sunsynk.net" if base_url is None else base_url
        self.session = session or aiohttp.ClientSession()
        self.access_token = None
        self.refresh_token = None
        self.username = username
        self.password = password

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        await self.session.close()

    async def get(self, url: str, params=None, attempts: int = 1):
        resp = await self.session.get(
            url, headers=self.__headers(), params=params, timeout=20
        )
        if resp.status == 401 and attempts == 1:
            await self.login()
            return await self.get(url, params=params, attempts=attempts + 1)
        return await resp.json()

    async def post(self, url, json, params=None, attempts: int = 1):
        resp = await self.session.post(
            url, headers=self.__headers(), params=params, timeout=20, json=json
        )
        if resp.status == 401 and attempts == 1:
            await self.login()
            return await self.post(url, json, params=params, attempts=attempts + 1)
        return await resp.json()

    def __headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def login(self):
        """Authenticate and store the access token."""
        raw_key = await self.__fetch_public_key()
        encrypted_password = self.__rsa_encrypt_pkcs1v15(raw_key, self.password)

        login_nonce = self.__make_nonce()
        login_sign = self.__md5_hex(
            f"nonce={login_nonce}&source={self._SOURCE}{raw_key[:10]}"
        )
        payload = {
            "username": self.username,
            "password": encrypted_password,
            "grant_type": "password",
            "client_id": self._CLIENT_ID,
            "source": self._SOURCE,
            "nonce": login_nonce,
            "sign": login_sign,
        }
        resp = await self.session.post(
            self.__url("oauth/token/new"),
            headers={"Content-Type": "application/json"},
            timeout=20,
            json=payload,
        )
        if resp.status == 200:
            resp_body = await resp.json()
            if resp_body["success"]:
                self.access_token = resp_body["data"]["access_token"]
                self.refresh_token = resp_body["data"]["refresh_token"]
                return self
        raise InvalidCredentialsException

    async def __fetch_public_key(self) -> str:
        nonce = self.__make_nonce()
        sign = self.__md5_hex(f"nonce={nonce}&source={self._SOURCE}POWER_VIEW")
        url = self.__url(
            f"anonymous/publicKey?nonce={nonce}&source={self._SOURCE}&sign={sign}"
        )
        resp = await self.session.get(
            url,
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        if resp.status != 200:
            raise InvalidCredentialsException
        body = await resp.json()
        if not body.get("success") or not body.get("data"):
            raise InvalidCredentialsException
        return body["data"]

    @staticmethod
    def __make_nonce() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def __md5_hex(value: str) -> str:
        return hashlib.md5(value.encode()).hexdigest()

    @staticmethod
    def __rsa_encrypt_pkcs1v15(raw_key: str, plaintext: str) -> str:
        pem = (
            f"-----BEGIN PUBLIC KEY-----\n{raw_key}\n-----END PUBLIC KEY-----".encode()
        )
        public_key = serialization.load_pem_public_key(pem)
        ciphertext = public_key.encrypt(plaintext.encode(), padding.PKCS1v15())
        return base64.b64encode(ciphertext).decode()

    def __url(self, path: str) -> str:
        return f"{self.base_url}/{path}"
