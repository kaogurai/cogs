import json
import re


class FifteenAIPlugin:
    """
    This plugin fully implements the undocumented 15.ai API.

    The URLs that are returned are completely valid and can be used to download the audio, but lavalink does not properly play them.
    """

    FIFTEEN_AI_API_URL = "https://api.15.ai/app/getAudioFile5"
    FIFTEEN_AI_CDN_URL = "https://cdn.15.ai/audio/"

    def __init__(self, voices, session):
        self.session = session
        self.voices = voices
        self.name = "15.ai"
        self.limit = 200

    async def generate_url(self, voice: str, text: str):
        text = re.sub(r"[0-9]", "", text)
        data = {
            "text": text[: self.limit],
            "character": self.voices[voice]["apiName"],
            "emotion": "Contextual",
        }
        async with self.session.post(self.FIFTEEN_AI_API_URL, data=data) as response:
            if response.status == 200:
                resp = await response.text()
                dict_resp = json.loads(resp)
                wav = dict_resp["wavNames"][1]
                url = self.FIFTEEN_AI_CDN_URL + wav
                return url
