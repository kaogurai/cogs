import json


class FestivalPlugin:

    FESTIVAL_BASE_URL = "https://www.cstr.ed.ac.uk/cgi-bin/cstr/festivalspeak.cgi"

    def __init__(self, voices, session):
        self.session = session
        self.voices = voices
        self.name = "Festival"
        self.limit = 70
        self.needs_request = True

    async def generate_url(self, voice: str, text: str):
        params = {
            "voice": self.voices[voice]["apiName"],
            "UserText": text[: self.limit],
            "AJAX": "on",
        }

        async with self.session.get(self.FESTIVAL_BASE_URL, params=params) as resp:
            if resp.status != 200:
                return None

            resp = await resp.text()
            split_first = resp.split("(")
            mainly_dict = split_first[1].strip()
            fully_seperated = mainly_dict.split(")")
            only_dict = fully_seperated[0].strip()
            replace_quotes = only_dict.replace("'", '"')
            loaded = json.loads(replace_quotes)
            url = loaded["wavurl"]
            return url
