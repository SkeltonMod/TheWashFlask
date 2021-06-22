from bs4 import BeautifulSoup
import requests
import constants
import random
from flask import g
import sqlite3
from sqlite3 import Error
import re

DATABASE = 'session.db'

create_table = """ CREATE TABLE IF NOT EXISTS temp_room (
                                        id integer PRIMARY KEY,
                                        username text NOT NULL,
                                        room text NOT NULL,
                                        real_name text NOT NULL,
                                        unique_key text NOT NULL,
                                        logged boolean NOT NULL
                                    ); """


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


def generate_channel_id(is_num=False):
    saltable_string = "1234567890abcdefghijklmnopqrstuvwxyz"
    saltable_string_num = "1234567890"
    channel_key = ""

    for x in range(10):
        channel_key += (saltable_string[random.randint(0, 35)] if is_num else saltable_string_num[random.randint(0, 9)])
    return channel_key


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

    get_headers = iframe_src.replace("//streamani.net/streaming.php?", "")

    # ALAS!
    response = requests.get(constants.STREAM_ANI_URL + get_headers).content
    bs = BeautifulSoup(response, "html.parser")
    return re.findall("('https:\/\/\S+')", str(bs.find_all('script', {"type": "text/JavaScript"})))


def get_db():
    con = sqlite3.connect(DATABASE)
    return con


def create_temp_table():
    con = get_db()
    cur = con.cursor()
    cur.execute(create_table)


def check_if_exists(user):
    sql = "SELECT * FROM temp_room WHERE real_name=?"
    con = get_db()
    cur = con.cursor()
    cur.execute(sql, (user, ))
    if cur.fetchone():
        return True
    else:
        return False


def check_if_exists_uq(user):
    sql = "SELECT * FROM temp_room WHERE unique_key=?"
    con = get_db()
    cur = con.cursor()
    cur.execute(sql, (user, ))
    if cur.fetchone():
        return True
    else:
        return False

def verify_username(user):
    sql = "SELECT * FROM temp_room WHERE real_name=?"
    con = get_db()
    cur = con.cursor()
    cur.execute(sql, (user,))
    return cur.fetchone()


def get_data(unique_key):
    sql = "SELECT * FROM temp_room WHERE unique_key=?"
    con = get_db()
    cur = con.cursor()
    cur.execute(sql, (unique_key,))
    return cur.fetchone()


def get_all_sessions():
    sql = "SELECT * FROM temp_room WHERE logged=1"
    con = get_db()
    cur = con.cursor()
    cur.execute(sql)
    return cur.fetchall()


def delete_session(query):
    sql = "DELETE FROM temp_room WHERE unique_key=?"
    con = get_db()
    cur = con.cursor()
    cur.execute(sql, (query, ))
    con.commit()


def create_temp_user(user):
    sql = "INSERT INTO temp_room(username, room, real_name, unique_key, logged) VALUES (?, ?, ?, ?, 1)"
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, user)
    conn.commit()
    print(cur.lastrowid)


# Deactivate Sessions
def edit_session(query):
    sql = "UPDATE temp_room SET logged=? WHERE unique_key=?"
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, query)
    conn.commit()
    pass
