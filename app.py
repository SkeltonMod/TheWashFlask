from flask import Flask, redirect, render_template, request, url_for, flash
from flask_mysqldb import MySQL
from flaskext.markdown import Markdown
import os
from datetime import datetime
from data import Entries, search, play
from bs4 import BeautifulSoup
from flask_caching import Cache
import feedparser as fp
from wtforms import Form, StringField, TextAreaField, validators

CONFIG = {
    "DEBUG": True,
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300
}
# FORWARD
app = Flask(__name__)
# Configure MYSQL
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'posts'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config.from_mapping(CONFIG)
Markdown(app)
mysql = MySQL(app)
cache = Cache(app)
app.secret_key = "malim123HAHAHAHAOTEN09292"


@app.route('/')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM content ORDER BY date DESC")
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
    print(data)
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


class EntryForm(Form):
    title = StringField("", [validators.Length(min=1, max=150), validators.DataRequired()])
    date = StringField("", [validators.Length(min=1, max=150)])
    author = StringField("", [validators.Length(min=1)], render_kw={"readonly": True})
    entry = TextAreaField("", [validators.Length(min=1)])


class AnimeSearch(Form):
    title = StringField("", [validators.length(min=1)])


@app.route('/editor', methods=['POST', 'GET'])
def add_entry():
    form = EntryForm(request.form)
    if request.method == "POST" and form.validate():
        # Get the Data
        title = form.title.data
        entry = form.entry.data
        date = datetime.strptime(form.date.data, "%Y-%m-%d")
        author = form.author.data
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
        print(sort_id)
        cursor.execute("INSERT INTO content(`file_name`, `date`, `title`, `author`, `sort_id`) VALUES(%s,%s,%s,%s,%s)",
                       (file_name, date, title, author, sort_id))
        mysql.connection.commit()
        flash("Entry Added!", "success")
        cursor.close()

    return render_template('editor.html', form=form)


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


@app.route('/player/<string:name>')
def playAnime(name):
    series = play(name)
    print(series)
    return render_template("player.html", info=series['info'], episodes=series['episodes'])


if __name__ == '__main__':
    app.run()
