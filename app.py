from flask import Flask, redirect, render_template, request, url_for, flash, jsonify, Blueprint, session
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
from wtforms import Form, StringField, TextAreaField, validators, PasswordField
from flask_socketio import SocketIO, join_room, leave_room, emit
app = Flask(__name__)
channel_list = list()
channel_messages = list()

CONFIG = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300
}
# Configure MYSQL
app.config['MYSQL_HOST'] = constants.HOST
app.config['MYSQL_USER'] = constants.USERNAME
app.config['MYSQL_PASSWORD'] = constants.PASSWORD
app.config['MYSQL_DB'] = constants.DB_NAME
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['SECRET_KEY'] = "malim123HAHAHAHAOTEN092921"
app.config.from_mapping(CONFIG)
Markdown(app)
mysql = MySQL(app)
cache = Cache(app)
cors = CORS(app)
socketio = SocketIO(app, async_mode=None, cors_allowed_origins=[])

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

class LoginForm(Form):
    username = StringField("", [validators.Length(min=1, max=150), validators.DataRequired()])
    password = PasswordField("", [validators.Length(min=1, max=150)])

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

@app.route('/api/underground', methods=['POST', 'GET'])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password = form.password.data

        if username == "Admin" and password == "malim890":
            session['room'] = "Super"
            session['user'] = "SuperUser"
            return render_template('wd_chat_admin.html', admin = True, session=session)

    return render_template('login.html', form=form)


# For the guest
# User ID and Room ID will be generated by the bot in the future
@app.route('/api/wd_chat', methods=['POST', 'GET'])
def chat():
    if len(session) == 0:
        session['room'] = generate_channel_id(False)
        session['user'] = generate_channel_id(True)
    print(session)
    print(len(session))
    if session['user'] == "SuperUser":
       return redirect(url_for('login'))
    else:
        return render_template('wd_chat.html', room_id=session['room'], user_id=session['user'])

@socketio.on('join channel')
def join_channel(data):
    print(f'Joined Room {data["room_id"]}')
    room = data["room_id"]
    join_room(room)
    socketio.emit('joined channel ack',broadcast=True, room=room)

@socketio.on('leave channel')
def leave_channel(data):
    print(f"Left Room {session.get('room')}")
    room = session.get('room')
    leave_room(room)
    for key, value in enumerate(channel_list):
        if data['room_id'] in value['room_id']:
            channel_list.pop(key)
    print(channel_list)
    socketio.emit('leave channel ack', room=room)

@socketio.on('kick user')
def kick_user(data):
    print(f"You are kicked from Room: {data['room_id']}")
    room = data['room_id']
    leave_room(room)
    for key, value in enumerate(channel_list):
        if data['room_id'] in value['room_id']:
            channel_list.pop(key)
    print(channel_list)
    channel_data = channel_list
    socketio.emit('user kicked',channel_data, room=room)


@socketio.on('send')
def send_message(data):
    print(data['message_data']['room_id'])
    room = data['message_data']['room_id']
    channel_messages.append({f"{session['room']}": data['message_data']})
    emit('broadcast message', data,broadcast=True, room=room)

@socketio.on('load message')
def load_message(data):
    print(data)
    # Load message from array
    # print(channel_messages['']['room_id'])
    # for key, value in enumerate(channel_messages):
    #     print(value[f"{data['room_id']}"])


@socketio.on('get channels')
def get_channels(data):
    channel_data = channel_list
    print(f"channel data: {channel_data}")
    emit('return channels', channel_data)

@socketio.on('create channel')
def create_channel(data):
    if len(channel_list) == 0 or data not in channel_list:
        channel_list.append(data)
    print(channel_list)
    # After creating the channel, Join it!
    room=session.get('room')
    join_room(room)
    emit('channel created', data, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=1024, debug=True)





