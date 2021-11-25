"""
This code is unlicensed and under exclusive copyright of github user apex2504

Source: https://github.com/apex2504/minimal-deezer-dl/
"""
import asyncio
import hashlib
from io import BytesIO

import aiohttp
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class Deezer:
    def __init__(self):  # vsc why complain
        self._initialised = False
        self.session_id = None
        self.api_token = None
        self.license_token = None
        self.http = None

    def get_blowfish_key(self, track_id):
        secret = "g4el58wc0zvf9na1"

        m = hashlib.md5()
        m.update(bytes([ord(x) for x in track_id]))
        id_md5 = m.hexdigest()

        blowfish_key = bytes(
            (
                [
                    (ord(id_md5[i]) ^ ord(id_md5[i + 16]) ^ ord(secret[i]))
                    for i in range(16)
                ]
            )
        )

        return blowfish_key

    async def initialise(self):
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://www.deezer.com/ajax/gw-light.php?method=deezer.getUserData&input=3&api_version=1.0&api_token="
            ) as r:
                data = await r.json()

        self.session_id = data["results"]["SESSION_ID"]
        self.api_token = data["results"]["checkForm"]
        self.license_token = data["results"]["USER"]["OPTIONS"]["license_token"]
        self._initialised = True
        self.http = aiohttp.ClientSession(headers={"cookie": f"sid={self.session_id}"})

    async def request(self, url, method, body, return_json=True):
        data = await self.http.request(method, url, json=body)
        if return_json:
            return await data.json()
        return data

    async def api(self, method, data):
        if not self._initialised:
            await self.initialise()

        return await self.request(
            f"https://www.deezer.com/ajax/gw-light.php?method={method}&input=3&api_version=1.0&api_token={self.api_token}",
            method="POST",
            body=data,
        )

    async def search(self, type_, query):
        res = await self.api(
            "deezer.pageSearch",
            {"query": query, "start": 0, "nb": 5, "top_tracks": True},
        )

        return res["results"][type_.upper()]["data"]

    async def download(self, track):
        dl_info = await self.request(
            "https://media.deezer.com/v1/get_url",
            "POST",
            {
                "license_token": self.license_token,
                "media": [
                    {
                        "type": "FULL",
                        "formats": [
                            {
                                "cipher": "BF_CBC_STRIPE",
                                "format": "MP3_128",
                            }
                        ],
                    }
                ],
                "track_tokens": [track["TRACK_TOKEN"]],
            },
        )
        url = dl_info["data"][0]["media"][0]["sources"][0]["url"]
        stream = await asyncio.get_running_loop().run_in_executor(
            None, lambda: requests.get(url, stream=True)
        )  # because i cant get aiohttp to work hhh
        # stream = await self.request(url, 'GET', {}, return_json=False)

        blowfish_key = self.get_blowfish_key(track["SNG_ID"])
        i = 0

        # with open(f'{filename}.mp3', 'wb') as f:
        f = BytesIO()
        for chunk in stream.iter_content(2048):

            if i % 3 > 0:
                f.write(chunk)
            elif len(chunk) < 2048:
                f.write(chunk)
                break
            else:
                cipher = Cipher(
                    algorithms.Blowfish(blowfish_key),
                    modes.CBC(bytes([i for i in range(8)])),
                    default_backend(),
                )

                decryptor = cipher.decryptor()
                dec_data = decryptor.update(chunk) + decryptor.finalize()
                f.write(dec_data)

            i += 1

        f.seek(0)
        return f
