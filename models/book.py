from extension import db

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(13), unique=True, nullable=False)
    publisher = db.Column(db.String(100), nullable=True)
    pages = db.Column(db.Integer, nullable=True)
    stock = db.Column(db.Integer, default=0)