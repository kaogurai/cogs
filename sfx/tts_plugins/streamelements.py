import urllib


class StreamElementsPlugin:

    STREAMELEMENTS_BASE_URL = "https://api.streamelements.com/kappa/v2/speech"

    def __init__(self, voices, session):
        self.session = session
        self.voices = voices
        self.name = "StreamElements"
        self.limit = 1000
        self.needs_request = False

    async def generate_url(self, voice: str, text: str):
        params = {
            "voice": self.voices[voice]["apiName"],
            "text": text[: self.limit],
        }

        url = f"{self.STREAMELEMENTS_BASE_URL}?{urllib.parse.urlencode(params)}"
        return url
