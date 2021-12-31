import urllib


class FestivalPlugin:

    FESTIVAL_BASE_URL = "https://www.cstr.ed.ac.uk/cgi-bin/cstr/festivalspeak.cgi"
    

    def __init__(self, voices, session):
        self.session = session
        self.voices = voices
        self.name = "Festival"
        self.limit = 70

    async def generate_url(self, voice: str, text: str):
        params = {
            "voice": self.voices[voice]["apiName"],
            "UserText": text[: self.limit],
            "AJAX": "on",
        }

        async with self.session.post(self.FESTIVAL_BASE_URL, params=params) as resp:
            if resp.status != 200:
                return None

            resp = await resp.text()
            # THIS DOESN'T WORK I NEED TO DO SOMETHING TO GET THE URL
            return resp

