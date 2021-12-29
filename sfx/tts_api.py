from .voices import voices


async def generate_url(self, voice: str, text: str, translate: bool):
    """
    Input: voice: str, text: str, speed: int
    Output: url:str
    """
    text = text[:1000]
    if translate:
        text = await _translate_text(self, voices[voice]["languageCode"], text)
    plugin = voices[voice]["api"](voices, self.session)
    url = await plugin.generate_url(voice, text)
    return url


async def _translate_text(self, lang, text):
    """
    Input: lang: str, text: str
    Output: text: str
    """
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
