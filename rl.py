import requests

for x in range(150):
    data = {
        "text": f"Hello World " + "A" * x,
        "character": "GLaDOS",
        "emotion": "Contextual"
    }
    print(data)
    r = requests.post("https://api.15.ai/app/getAudioFile5", data=data)
    print(x, r.status_code)