from extension import db
from datetime import datetime

class Transaction(db.Model):
    __tablename__ = "transaction"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)

    issue_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    return_date = db.Column(db.DateTime)

    fee = db.Column(db.Float, default=0)

    book = db.relationship("Book")
    member = db.relationship("Member")
