import urllib

from .base import TTSPlugin


class MaryTTSPlugin(TTSPlugin):

    MARYTTS_BASE_URL = "http://fiware.tts.mivoq.it/process"

    async def generate_url(self, voice: str, translate: bool, text: str):
        if translate:
            langcode = self.voices[voice]["languageCode"]
            text = await self.translate_text(self, langcode, text)

        params = {
            "INPUT_TEXT": text,
            "INPUT_TYPE": "TEXT",
            "OUTPUT_TYPE": "AUDIO",
            "AUDIO": "WAVE_FILE",
            "LOCALE": self.voices[voice]["languageCode"],
            "VOICE": self.voices[voice]["apiName"],
        }

        url = f"{self.MARYTTS_BASE_URL}?{urllib.parse.urlencode(params)}"
        return url
