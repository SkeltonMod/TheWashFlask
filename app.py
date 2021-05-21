from flask import Flask, redirect, render_template, request, url_for, abort, session
from flask_mysqldb import MySQL
from flaskext.markdown import Markdown
import os
from datetime import datetime
import data
from data import Entries
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
app.config['SECRET_KEY'] = '123444444312312'

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
        series = data.search(form.title.data)
    return render_template("anime.html", series=series, form=form)


@app.route('/player/<string:name>/<string:episode>', methods=["GET", "POST"])
def playAnime(name, episode):
    series = data.getAnime(name)
    media = data.play(f"/{episode}")
    sort_by = data.getAnime(name)
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
            return render_template('wd_chat_admin.html', admin=True, session=session)

    return render_template('login.html', form=form)


# For the guest
# User ID and Room ID will be generated by the bot in the future
@app.route('/api/boot/<string:name>', methods=['POST', 'GET'])
def chat(name):
    if not data.check_if_exists(name):
        unique_key = data.generate_channel_id(False)
        session['unique_key'] = unique_key
        data.create_temp_user((data.generate_channel_id(True), data.generate_channel_id(False), name, unique_key))

    session_var = data.check_if_logged(name)
    print(session_var)
    try:
        print(session['unique_key'])
        if session['unique_key'] == session_var[4]:
            return render_template('wd_chat.html', room_id=session_var[2], user_id=session_var[1])
    except KeyError:
        return redirect(url_for('disconnected'))

    return render_template('404.html')


@app.route('/disconnected')
def disconnected():
    if len(session) == 0:
        abort(401)
    return render_template('disconnected.html')


@socketio.on('join channel')
def join_channel(info_data):
    print(f'Joined Room {info_data["room_id"]}')
    room = info_data["room_id"]
    join_room(room)
    socketio.emit('joined channel ack', broadcast=True, room=room)


@socketio.on('leave channel')
def leave_channel(info_data):
    print(f"Left Room {session.get('room')}")
    room = session.get('room')
    leave_room(room)
    data.delete_session((info_data['room_id'], info_data['user_id']))
    session.clear()
    socketio.emit('leave channel ack', room=room)


@socketio.on('kick user')
def kick_user(info_data):
    print(f"You are kicked from Room: {info_data['room_id']}")
    room = info_data['room_id']
    leave_room(room)
    data.delete_session((info_data['room_id'], info_data['user_id']))
    session.clear()
    socketio.emit('user kicked', {}, room=room)


@socketio.on('send')
def send_message(info_data):
    print(info_data['message_data']['room_id'])
    room = info_data['message_data']['room_id']
    emit('broadcast message', info_data, broadcast=True, room=room)


@socketio.on('load message')
def load_message(data):
    print(data)


@socketio.on('get channels')
def get_channels(info_data):
    channel_data = {'channel': data.get_all_sessions()}
    print(f"channel data: {channel_data}")
    emit('return channels', channel_data)


@socketio.on('create channel')
def create_channel(channel_data):
    temp = data.get_data(session['unique_key'])
    room = temp[2]
    print(f"Room {room}")
    join_room(room)
    emit('channel created', channel_data, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=1024, debug=True)

# Create Table
data.create_temp_table()
