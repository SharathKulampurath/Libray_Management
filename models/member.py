from extension import db

class Member(db.Model):
    __tablename__ = "member"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    outstanding_fees = db.Column(db.Float, default=0)
