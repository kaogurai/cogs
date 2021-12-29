import aiohttp


class TTSPlugin:
    def __init__(self, voices, session: aiohttp.ClientSession):
        self.session = session
        self.voices = voices

    async def translate_text(self, lang, text):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36"
        }
        params = {"client": "dict-chrome-ex", "tl": lang, "q": text}
        async with self.session.get(
            "https://clients5.google.com/translate_a/t", headers=headers, params=params
        ) as request:
            if request.status == 200:
                j = await request.json()
                r = j["sentences"]
                results = ""
                for response in r:
                    if "trans" in response.keys():
                        results += response["trans"]
                return results
            return text
