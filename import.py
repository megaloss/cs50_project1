import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    next(reader);
    for isbn, name, author, year in reader:
        print(f"Added book {name} by {author} written in {year}.")
        db.execute("INSERT INTO books (isbn, name, author, year) VALUES (:isbn, :name, :author, :year)",
            {"isbn": isbn, "name": name, "author": author, "year": year })
    db.commit()

if __name__ == "__main__":
    main()
