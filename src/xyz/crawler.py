import requests, io
from src.utilities import timed_func

@timed_func
def get_audio_stream(url):
    response = requests.get(url)
    html = response.text

    print("html got")

    m4a_urls = []
    start_pos = 0
    while True:
        start_pos = html.find('.m4a', start_pos)
        if start_pos == -1:  # no more .m4a found
            print("no more m4a url found, let's break")
            break
        # find the start of the URL
        url_start_pos = html.rfind('http', 0, start_pos)
        # find the end of the URL
        url_end_pos = start_pos + len('.m4a')
        # extract the URL
        m4a_url = html[url_start_pos:url_end_pos]
        # check duplication
        if (m4a_url not in [url for url in m4a_urls]):
            m4a_urls.append(m4a_url)
            print(m4a_url)
        # move to the next position
        start_pos = url_end_pos

    if len(m4a_urls) == 0:
        return None, None

    response = requests.get(m4a_urls[0], stream=True)
    response.raise_for_status()

    file_stream = io.BytesIO()
    for chunk in response.iter_content(chunk_size=8192):
        file_stream.write(chunk)
    file_stream.seek(0)

    return file_stream, m4a_urls[0].split(".")[-1]
