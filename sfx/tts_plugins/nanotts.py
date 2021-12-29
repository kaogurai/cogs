from .base import TTSPlugin


class NanoTTSPlugin(TTSPlugin):

    NANOTTS_DOMAIN = "https://nanottsaas.herokuapp.com"
    NANOTTS_API_URL = f"{NANOTTS_DOMAIN}/api"

    async def generate_url(self, voice: str, translate: bool, text: str):
        if translate:
            langcode = self.voices[voice]["languageCode"]
            text = await self.translate_text(self, langcode, text)

        data = {
            "text": text,
            "voice": self.voices[voice]["apiName"],
            "response_type": "audio_address",
            "speed": "",
            "pitch": "",
        }
        async with self.session.post(f"{self.NANOTTS_API_URL}", data=data) as request:
            if request.status == 200:
                j = await request.json()
                url = self.NANOTTS_DOMAIN + j["audio_file"]
                return url
