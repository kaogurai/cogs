import urllib

from .base import TTSPlugin


class NaverPlugin(TTSPlugin):

    NAVER_BASE_URL = "https://en.dict.naver.com/api/nvoice"

    async def generate_url(self, voice: str, translate: bool, text: str):
        if translate:
            langcode = self.voices[voice]["languageCode"]
            text = await self.translate_text(self, langcode, text)
        params = {
            "speaker": self.voices[voice]["apiName"],
            "service": "dictionary",
            "speech_fmt": "mp3",
            "text": text,
            "volume": 5,
        }

        url = f"{self.NAVER_BASE_URL}?{urllib.parse.urlencode(params)}"
        return url
