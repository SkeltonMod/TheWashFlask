from flask import Flask, redirect, render_template, request, url_for, abort, session, json
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
app.config['SECRET_KEY'] = '12344444431231111'

app.config.from_mapping(CONFIG)
Markdown(app)
mysql = MySQL(app)
cache = Cache(app)
cors = CORS(app)
socketio = SocketIO(app, async_mode=None, cors_allowed_origins=[])
global_session = None

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
                           media=str(media[0]).replace('\'', ""), sort_by=sort_by['sort_by'])


@app.route('/api/underground', methods=['POST', 'GET'])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password = form.password.data

        if username == "Admin" and password == "malim890":
            session['room'] = "Super"
            session['user'] = "SuperUser"
            session['admin_unique_key'] = "sajuk"
            return render_template('wd_chat_admin.html', admin=True, session=session)

    return render_template('login.html', form=form)


@app.route('/404')
def err():
    return render_template('404.html')


# For the guest
# User ID and Room ID will be generated by the bot in the future
@app.route('/api/boot/<string:facebook_id>')
def boot(facebook_id):
    session_vars = None
    # session.clear()
    # print(session['unique_key'])
    if not data.check_if_exists(facebook_id) and session.get('unique_key'):
        abort(401)

    try:
        # If user doesn't exist then create a new one
        if not data.check_if_exists(facebook_id) and not session.get('unique_key'):
            unique_key = data.generate_channel_id(False)
            session['unique_key'] = unique_key
            data.create_temp_user((data.generate_channel_id(True), data.generate_channel_id(False),
                                   facebook_id, unique_key))
        # get the data
        session_vars = data.verify_username(facebook_id)
        print(session_vars)

    except KeyError:
        abort(401)
    return render_template('setup.html', session_vars=session_vars)


@app.route('/api/verification/', methods=['GET'])
def verify():
    if request.method == "GET":
        if request.args.get('key') == 'init':
            try:
                if request.args.get('unique_key') == session['unique_key'] and request.args.get('unique_key'):
                    if data.check_if_exists_uq(session.get('unique_key')):
                        # log back in
                        if data.get_data(session.get('unique_key'))[5] == 0:
                            data.edit_session((1, session.get('unique_key')))
                    return json.dumps({'status': 'OK'})
                else:
                    print(session.get('unique_key'))
                    return json.dumps({'status': 'INVALID'})
            except KeyError:
                print("FATAL ERROR")
                print(session.get('unique_key'))
                return json.dumps({'status': 'FATAL_ERROR'})


@app.route('/api/wd_chat/', methods=['GET'])
def chat():
    if not session.get('unique_key'):
        abort(401)
    session_vars = data.get_data(session['unique_key'])
    if session_vars[5] == 0:
        return redirect(url_for('err'))
    return render_template('wd_chat.html', session_vars=session_vars)


@socketio.on('join channel')
def join_channel(channel_data):
    room = channel_data['room']
    join_room(room)
    socketio.emit('channel joined', channel_data, room=room)


@socketio.on('leave channel')
def leave_channel(channel_data):
    global global_session
    room = channel_data['room']
    leave_room(room)
    data.edit_session((0, session['unique_key']))
    socketio.emit('channel leave', channel_data, room=room)


@socketio.on('send message')
def send(message_data):
    print(message_data)
    room = message_data['room']
    socketio.emit('broadcast message', message_data, broadcast=True, room=room)


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=1024, debug=True)

# Create Table
data.create_temp_table()
