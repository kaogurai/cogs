import urllib.parse

from sfx.voices import voices

ramp = {
    0: 5,
    1: 4,
    2: 3,
    3: 2,
    4: 1,
    5: 0,
    6: -1,
    7: -2,
    8: -3,
    9: -4,
    10: -5,
}
reversed_ramp = {0: -5, 1: -4, 2: -3, 3: -2, 4: -1, 5: 0, 6: 1, 7: 2, 8: 3, 9: 4, 10: 5}


def _split_text(voice: str, text: str):
    """
    Input: voice: str, text: str
    Output: list of str
    """
    limit = voices[voice]["limit"]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def _convert_stuff(num: int):
    return int(ramp[num])


def _convert_stuff_reversed(num: int):
    return int(reversed_ramp[num])


async def generate_urls(
    self, voice: str, text: str, speed: int, volume: int, translate: bool
):
    """
    Input: voice: str, text: str, speed: int
    Output: list of str (urls)
    """
    lang = voices[voice]["languageCode"]
    if translate:
        maybe_text = await _translate_text(self, lang, text)
        if maybe_text:
            text = maybe_text
    texts = _split_text(voice, text)
    url = "https://en.dict.naver.com/api/nvoice?speaker={voice}&service=dictionary&speech_fmt=mp3&text={text}&speed={speed}&volume={volume}"
    urls = []
    for segment in texts:
        turl = url
        turl = turl.replace("{text}", str(urllib.parse.quote(segment)))
        turl = turl.replace("{speed}", str(_convert_stuff(speed)))
        turl = turl.replace("{voice}", voices[voice]["api_name"])
        turl = turl.replace("{volume}", str(_convert_stuff_reversed(volume)))
        urls.append(turl)
    return urls


async def _translate_text(self, lang, text):
    """
    Input: lang: str, text: str
    Output: str
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36"
    }
    params = {"client": "dict-chrome-ex", "tl": lang, "q": text}
    async with self.session.get(
        "https://clients5.google.com/translate_a/t", headers=headers, params=params
    ) as request:
        if request.status == 200:
            j = await request.json()
            r = j["sentences"]
            results = ""
            for response in r:
                if "trans" in response.keys():
                    results += response["trans"]
            return results
