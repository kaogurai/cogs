import urllib


class GoogleTranslatePlugin:

    GOOGLE_TRANSLATE_BASE_URL = "https://translate.google.com/translate_tts"

    def __init__(self, voices, session):
        self.session = session
        self.voices = voices
        self.name = "Google Translate"

    async def generate_url(self, voice: str, text: str):
        params = {
            "ie": "UTF-8",
            "client": "tw-ob",
            "tl": self.voices[voice]["apiName"],
            "q": text,
        }

        url = f"{self.GOOGLE_TRANSLATE_BASE_URL}?{urllib.parse.urlencode(params)}"
        return url
