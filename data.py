from bs4 import BeautifulSoup
import requests
import constants


def Entries(arr):  # ACCEPTS LIST
    dates = list()
    for x in range(len(arr)):
        dates.append(
            f"{arr[x].get('sort_id')}, {arr[x].get('date').strftime('%B')}, {arr[x].get('date').year}")

    return tally_months(dates)


def tally_months(arr):
    arr.sort()
    prev = ""
    a = list()
    b = list()
    # glued together

    c = list()
    for x in arr:
        if x != prev:
            a.append(x)
            b.append(1)
        else:
            b[len(b) - 1] += 1
        prev = x

    # now that we're done counting let's piece them together
    for x in range(len(a)):
        split = a[x].split(", ")
        c.append({"tally": f"{split[1]}, {split[2]} ({b[x]})", "sort_id": split[0]})

    return c


def search(keyword):
    response = requests.get(constants.SEARCH_URL + keyword.replace(" ", "-").lower()).content
    bs = BeautifulSoup(response, "html.parser")
    anime = list()
    for a in bs.find_all("a", href=True):
        if str(keyword).lower() in str(a.text).lower():
            anime.append({"title": a.text, "link": a['href'], 'name': str(a.text).replace(" ", "-").lower(),
                          "serialized_name": str(a['href']).replace("/category/", "")})
    return anime


def getAnime(keyword):
    response = requests.get(constants.SERIES_URL + keyword.replace(" ", "-").lower()).content
    bs = BeautifulSoup(response, "html.parser")
    info = list()
    episodes = list()
    souped = dict()

    # Get Anime Info
    for p in bs.find_all("p", class_="type"):
        info.append({p.text.split(":")[0]: p.text.split(":")[1]})
    souped['info'] = info

    # Get Anime Episodes
    response = requests.get(constants.SERIES_URL + keyword).content
    bs = BeautifulSoup(response, "html.parser")
    info = list()
    for eplist in bs.find("ul", {"id": "episode_page"}).find_all("a"):
        info.append({"end": eplist['ep_end'], "start": eplist['ep_start']})
    movie_id = bs.find("input", {"id": "movie_id"}).get('value')
    info.insert(0, {"movie_id": movie_id})
    response = requests.get(constants.EPLIST_URL +
                            f"ep_start={info[1]['start']}&ep_end={info[1]['end']}&id={info[0]['movie_id']}&default_ep"
                            f"=0&alias={keyword}").content
    bs = BeautifulSoup(response, "html.parser")
    for ep in bs.find("ul", id="episode_related").find_all("li"):
        episodes.append({ep.div.text: str(ep.a['href']).replace(" ", "")})

    souped['episodes'] = episodes
    souped['sort_by'] = info
    return souped


def play(keyword):
    # Get Current Anime Episode
    response = requests.get(constants.EPISODE_URL + keyword).content
    bs = BeautifulSoup(response, "html.parser")
    iframe_src = ""
    for iframe in bs.find_all("iframe"):
        iframe_src = iframe['src']

    # get ID and title GET Headers
    get_headers = iframe_src.replace("//gogo-play.net/streaming.php?", "")
    response = requests.get(constants.EPISODE_MEDIA_URL + get_headers)
    return response.json()
