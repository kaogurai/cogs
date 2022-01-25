import urllib


class MaryTTSPlugin:

    MARYTTS_BASE_URL = "http://fiware.tts.mivoq.it/process"

    def __init__(self, voices, session):
        self.session = session
        self.voices = voices
        self.name = "MaryTTS"
        self.limit = 1000
        self.needs_request = False

    async def generate_url(self, voice: str, text: str):
        params = {
            "INPUT_TEXT": text[: self.limit],
            "INPUT_TYPE": "TEXT",
            "OUTPUT_TYPE": "AUDIO",
            "AUDIO": "WAVE_FILE",
            "LOCALE": self.voices[voice]["languageCode"],
            "VOICE": self.voices[voice]["apiName"],
        }

        url = f"{self.MARYTTS_BASE_URL}?{urllib.parse.urlencode(params)}"
        return url
