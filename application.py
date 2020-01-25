import os

from flask import Flask, render_template, request, session, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt
from flask_session import Session
import requests


app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if session.get('user') is None:
        return render_template("login.html",message="Please login to use the site")
    books = db.execute("SELECT * FROM books ORDER BY name").fetchall()
    return render_template("index1.html", books=books)

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/signup_submit", methods=["POST"])

def signup_submit():
    login=request.form.get("login")
    passw=request.form.get("passw")
    name=request.form.get("name")
    passw_hash = sha256_crypt.encrypt(str(passw))
    if db.execute("SELECT * FROM users WHERE login = :login", {"login": login}).rowcount == 1:
        return render_template("error.html", message="User exists.")
    db.execute("INSERT INTO users (login, passw, name) VALUES (:login, :passw_hash, :name)", {"login": login, "passw_hash":passw_hash, "name":name}).fetchone

    db.commit()

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    return render_template("login.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/login_submit", methods=["POST"])
def login_submit():
    login=request.form.get("login")
    passw=request.form.get("passw")
    #passw_hash = sha256_crypt.encrypt("passw")

    user = db.execute("SELECT * FROM users WHERE login = :login", {"login": login}).fetchone()
    if user is None:
        return render_template("error.html", message="No such user.")

    #return render_template("error.html", message=user)


    if sha256_crypt.verify (passw, user.passw)==False:
        return render_template("error.html", message="Wrong password")


    session['user']=user.name
    session['user_id']=user.id
    return render_template("index1.html")

@app.route("/s/", methods=["GET"])
def search():
    if session.get('user') is None:
        return render_template("login.html", message="You must be logged in to search")
    s=request.args.get('search')
    s="%"+s+"%"
    books = db.execute("SELECT * FROM books WHERE name ILIKE :s ORDER BY name",{"s":s}).fetchall()
    return render_template("books.html", books=books)

@app.route("/review", methods=["POST"])
def review():
    if session.get('user') is None:
        return render_template("login.html",message="Please, log in first")
    """Review a book."""
    # Get form information.
    review = request.form.get("review")
    score = request.form.get("score")

    try:
        id = int(request.form.get("id"))
    except ValueError:
        return render_template("error.html", message="Invalid book number.")

    # Make sure book exists.
    if db.execute("SELECT * FROM books WHERE id = :id", {"id": id}).rowcount == 0:
        return render_template("error.html", message="No such book with that id.")
    name = session.get('user_id')
    db.execute("INSERT INTO reviews ( book_id, review, user_id, score) VALUES (:id, :review, :name, :score)",
            {"review": review, "id": id, "name": name, "score":score})
    db.commit()
    return render_template("success.html")

@app.route("/books")
def flights():
    if session.get('user') is None:
        return render_template("login.html", message="Please log in to use the site")
    """Lists all books."""
    books = db.execute("SELECT * FROM books").fetchall()
    return render_template("books.html", books=books)

@app.route("/api/<isbn>")
def isbn(isbn):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
    if book is None:
        return jsonify({"error": "Invalid book ibsn"}), 404

    id = book.id
    count = db.execute("SELECT review FROM reviews WHERE book_id = :id",{"id":id}).rowcount
    score = db.execute("SELECT AVG(score) FROM reviews WHERE book_id = :id",{"id":id}).fetchone()
    print (score[0])
    avg_score=float(score[0])
    return jsonify({
              "title": book.name,
              "author": book.author,
              "year": book.year,
              "isbn": book.isbn,
              "review_count": count,
              "average_score": avg_score
          })




@app.route("/books/<int:id>")
def book(id):
    if session.get('user') is None:
        return render_template("login.html")
    """Lists details about a single flight."""

    # Make sure flight exists.
    book = db.execute("SELECT * FROM books WHERE id = :id",{"id":id}).fetchone()
    reviews = db.execute("SELECT reviews.review, reviews.score, users.name, users.id FROM reviews INNER JOIN users ON reviews.user_id=users.id WHERE book_id = :id",{"id":id}).fetchall()
    score = db.execute("SELECT AVG(score) FROM reviews WHERE book_id = :id",{"id":id}).fetchone()
    avg_score=0
    if score[0] is not None:
        avg_score=float(score[0])

    isreviewed=""
    for review in reviews:
        if review[3]==session.get('user_id'):
            isreviewed="disabled"
    if book is None:
        return render_template("error.html", message="No such book.")

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"kzG3n0hzFE4nLy1TscTL5w": "KEY", "isbns": book.isbn})
    return render_template("book.html", avg_score=avg_score, book=book, reviews=reviews, rating=res.json(), isreviewed=isreviewed)
