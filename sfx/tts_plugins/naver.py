import urllib


class NaverPlugin:

    NAVER_BASE_URL = "https://en.dict.naver.com/api/nvoice"

    def __init__(self, voices, session):
        self.session = session
        self.voices = voices
        self.name = "Naver"

    async def generate_url(self, voice: str, text: str):
        params = {
            "speaker": self.voices[voice]["apiName"],
            "service": "dictionary",
            "speech_fmt": "mp3",
            "text": text,
            "volume": 5,
        }

        url = f"{self.NAVER_BASE_URL}?{urllib.parse.urlencode(params)}"
        return url
