from flask import Flask, redirect, render_template, request, url_for, flash, jsonify
from flask_mysqldb import MySQL
from flaskext.markdown import Markdown
import os
from datetime import datetime
from data import Entries, search, getAnime, play, download, generate_channel_id
from bs4 import BeautifulSoup
from flask_caching import Cache
import feedparser as fp
import constants
from flask_cors import CORS
from wtforms import Form, StringField, TextAreaField, validators
from flask_socketio import SocketIO

CONFIG = {
    "DEBUG": True,
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300
}
# FORWARD
app = Flask(__name__)
# Configure MYSQL
app.config['MYSQL_HOST'] = constants.HOST
app.config['MYSQL_USER'] = constants.USERNAME
app.config['MYSQL_PASSWORD'] = constants.PASSWORD
app.config['MYSQL_DB'] = constants.DB_NAME
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config.from_mapping(CONFIG)
Markdown(app)
mysql = MySQL(app)
cache = Cache(app)
app.secret_key = "malim123HAHAHAHAOTEN09292"
cors = CORS(app)
socketio = SocketIO(app)


@app.route('/')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM content ORDER BY id DESC")
    result = list(cur.fetchall())
    data = list()
    navlinks = getLinks()
    for idx, x in enumerate(range(len(result))):
        f = open(os.getcwd() + "/entries/" + result[x].get("file_name") + ".md", "r")
        temp_str = f.read()
        bs = BeautifulSoup(temp_str, "html.parser")
        result[x].update({"excerpt": bs.get_text()[0:144]})
        data.append(result[x])
        if idx > 4:
            break
    return render_template("home.html", entries=data, month=Entries(result), navlinks=navlinks,
                           now=datetime.date(datetime.now()))


@app.route('/entry/<string:id>/<string:title>')
def entry(id, title):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM content WHERE id = %s", [id])
    data = cur.fetchone()
    f = open(os.getcwd() + "/entries/" + data.get('file_name') + ".md", "r")
    return render_template('entry.html', entry=data, body=f.read(), title=title)


@app.route('/404')
def notFound():
    return render_template("404.html")


def getLinks():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, title,file_name, sort_id FROM content")
    data = cur.fetchall()
    return data


class AnimeSearch(Form):
    title = StringField("", [validators.length(min=1)])


@app.route('/getfile', methods=['POST', 'GET'])
def poll_entry():
    title = request.json['name']
    entry = request.json['content']
    date = datetime.strptime(request.json['date'], "%Y-%m-%d")
    author = request.json['author']
    # Append to File

    file_name = title.replace(" ", "_")

    try:
        file = open(os.getcwd() + "/entries/" + file_name + ".md", "x")
    except FileExistsError:
        count = len([name for name in os.listdir("./entries/") if file_name in name])
        file_name = f"{file_name}{count}"
        file = open(f"{os.getcwd()}/entries/{file_name}.md", "x")
        file.write(entry)
        file.close()
    else:
        file.write(entry)
        file.close()

    # generate sort_id
    sort_id = date.strftime("%m%Y").lstrip("0").replace(" 0", "")
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO content(`file_name`, `date`, `title`, `author`, `sort_id`) VALUES(%s,%s,%s,%s,%s)",
                   (file_name, date, title, author, sort_id))
    mysql.connection.commit()
    cursor.close()
    return f"Data: {request.json}"


@app.route('/wash')
def getRSS():
    rss = fp.parse("https://myanimelist.net/rss.php?type=rw&u=lil_fuckface")
    return render_template("wash.html", rss_entries=rss.entries, rss_feed=rss.feed)


@app.route('/anime', methods=['POST', 'GET'])
def searchAnime():
    series = dict()
    form = AnimeSearch(request.form)
    if request.method == "POST":
        series = search(form.title.data)
    return render_template("anime.html", series=series, form=form)


@app.route('/player/<string:name>/<string:episode>', methods=["GET", "POST"])
def playAnime(name, episode):
    series = getAnime(name)
    media = play(f"/{episode}")
    sort_by = getAnime(name)
    sort_by['sort_by'].pop(0)
    return render_template("player.html", info=series['info'], episodes=series['episodes'], title=name,
                           media=media["source"][0]['file'], sort_by=sort_by['sort_by'])


@app.route('/api/wd_chat', methods=['POST', 'GET'])
def chat():
        if request.method == "GET":
            if request.args.get('secret_key') == "8930493844443":
                return render_template('wd_chat_admin.html')
        return render_template('wd_chat.html', admin = False)

@socketio.on('send message')
def send_message(message):
    socketio.emit('recieve message', message)

@socketio.on('create channel')
def create_channel(username, user_id):
    channel_data = {
        "channel_key": generate_channel_id(),
        "channel_user" : username,
        "channel_user_id": user_id
    }
    print(f"Channel created {channel_data}")
    socketio.emit('channel created', channel_data)

if __name__ == '__main__':
    app.run()
