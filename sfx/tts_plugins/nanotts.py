class NanoTTSPlugin:

    NANOTTS_DOMAIN = "https://nanottsaas.herokuapp.com"
    NANOTTS_API_URL = f"{NANOTTS_DOMAIN}/api"

    def __init__(self, voices, session):
        self.session = session
        self.voices = voices
        self.name = "NanoTTS"

    async def generate_url(self, voice: str, text: str):
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
