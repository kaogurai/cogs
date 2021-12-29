from .tts_plugins.marytts import MaryTTSPlugin
from .tts_plugins.nanotts import NanoTTSPlugin
from .tts_plugins.naver import NaverPlugin
from .voices import voices


async def generate_url(self, voice: str, text: str, translate: bool):
    """
    Input: voice: str, text: str, speed: int
    Output: url:str
    """
    text = text[:1000]
    lang = voices[voice]["languageCode"]
    if translate:
        maybe_text = await _translate_text(self, lang, text)
        if maybe_text:
            text = maybe_text
    if voices[voice]["api"] == "Naver":
        url = await NaverPlugin(voices, self.session).generate_url(voice, translate, text)
    elif voices[voice]["api"] == "MaryTTS":
        url = await MaryTTSPlugin(voices, self.session).generate_url(
            voice, translate, text
        )
    elif voices[voice]["api"] == "NanoTTS":
        url = await NanoTTSPlugin(voices, self.session).generate_url(
            voice, translate, text
        )
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
