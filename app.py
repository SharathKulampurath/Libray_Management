from flask import Flask, render_template, request, redirect, url_for
from extension import db
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def request_api(url, params):
    return requests.get(url, params=params, verify=False).json()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config")

    # initialize database
    db.init_app(app)

    # import routes AFTER db initialized
    with app.app_context():
        from models.book import Book
        from models.member import Member    
        from models.transaction import Transaction
        db.create_all()

    return app


app = create_app()


# ---- ROUTES ----
@app.route("/")
def home():
    return "WELCOME TO THE LIBRARY MANAGEMENT SYSTEM"


@app.route("/books")
def books():
    from models.book import Book
    all_books = Book.query.all()
    return render_template("books.html", books=all_books)


@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    from models.book import Book
    if request.method == "POST":
        new_book = Book(
            title=request.form["title"],
            author=request.form["author"],
            isbn=request.form["isbn"],
            publisher=request.form["publisher"],
            pages=request.form["pages"],
            stock=request.form["stock"],
        )
        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for("books"))
    return render_template("add_book.html")


@app.route("/books/edit/<int:id>", methods=["GET", "POST"])
def edit_book(id):
    from models.book import Book
    book = Book.query.get_or_404(id)

    if request.method == "POST":
        book.title = request.form["title"]
        book.author = request.form["author"]
        book.isbn = request.form["isbn"]
        book.publisher = request.form["publisher"]
        book.pages = request.form["pages"]
        book.stock = request.form["stock"]
        db.session.commit()
        return redirect(url_for("books"))

    return render_template("edit_book.html", book=book)


@app.route("/books/delete/<int:id>")
def delete_book(id):
    from models.book import Book
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for("books"))


@app.route("/members")
def members():
    from models.member import Member
    all_members = Member.query.all()
    return render_template("members.html", members=all_members)

@app.route("/members/add", methods=["GET", "POST"])
def add_member():
    from models.member import Member
    if request.method == "POST":
        new_member = Member(
            name=request.form["name"],
            outstanding_fees=request.form["outstanding_fees"]
        )
        db.session.add(new_member)
        db.session.commit()
        return redirect(url_for("members"))

    return render_template("add_member.html")


@app.route("/members/edit/<int:id>", methods=["GET", "POST"])
def edit_member(id):
    from models.member import Member
    member = Member.query.get_or_404(id)

    if request.method == "POST":
        member.name = request.form["name"]
        member.outstanding_fees = request.form["outstanding_fees"]
        db.session.commit()
        return redirect(url_for("members"))

    return render_template("edit_member.html", member=member)


@app.route("/members/delete/<int:id>")
def delete_member(id):
    from models.member import Member
    member = Member.query.get_or_404(id)
    db.session.delete(member)
    db.session.commit()
    return redirect(url_for("members"))

@app.route("/transactions")
def transactions():
    from models.transaction import Transaction
    all_txn = Transaction.query.order_by(Transaction.id.desc()).all()
    return render_template("transactions.html", txns=all_txn)

@app.route("/issue", methods=["GET", "POST"])
def issue_book():
    from models.book import Book
    from models.member import Member
    from models.transaction import Transaction

    books = Book.query.all()
    members = Member.query.all()

    if request.method == "POST":
        book_id = request.form["book_id"]
        member_id = request.form["member_id"]

        book = Book.query.get(book_id)
        member = Member.query.get(member_id)

        # Check fee limit
        if member.outstanding_fees > 500:
            return "Member owes more than ₹500. Cannot issue book."

        # Check stock
        if book.stock <= 0:
            return "Book out of stock!"

        # Issue logic
        book.stock -= 1
        new_txn = Transaction(book_id=book_id, member_id=member_id)

        db.session.add(new_txn)
        db.session.commit()

        return redirect(url_for("transactions"))

    return render_template("issue.html", books=books, members=members)

@app.route("/return/<int:txn_id>", methods=["GET", "POST"])
def return_book(txn_id):
    from models.transaction import Transaction
    from models.book import Book
    from datetime import datetime

    txn = Transaction.query.get_or_404(txn_id)

    if request.method == "POST":
        txn.return_date = datetime.utcnow()

        # Calculate fee
        days = (txn.return_date - txn.issue_date).days
        extra_days = max(0, days - 7)
        txn.fee = extra_days * 10  # ₹10 per extra day

        # Update member fee
        member = txn.member
        member.outstanding_fees += txn.fee

        # Increase stock after return
        book = txn.book
        book.stock += 1

        db.session.commit()

        return redirect(url_for("transactions"))

    return render_template("return.html", txn=txn)


@app.route("/import_books", methods=["GET", "POST"])
def import_books():
    preview = []
    action = request.form.get("action")

    # --------------------------
    # ✅ SEARCH ACTION
    # --------------------------
    if request.method == "POST" and action == "search":
        title = (request.form.get("title") or "").strip()

        url = "https://frappe.io/api/method/frappe-library"
        params = {"title": title, "page": 1}

        response = request_api(url, params)
        raw = response.get("message", [])

        # ✅ CLEAN KEYS (strip spaces like "  num_pages")
        preview = []
        for b in raw:
            cleaned = {k.strip(): v for k, v in b.items()}
            preview.append(cleaned)

        return render_template("import_books.html", preview=preview)

    # --------------------------
    # ✅ IMPORT ACTION
    # --------------------------
    if request.method == "POST" and action == "import":
        from models.book import Book

        title = (request.form.get("title") or "").strip()
        count = int(request.form.get("count"))

        imported = 0
        page = 1

        while imported < count:
            url = "https://frappe.io/api/method/frappe-library"
            params = {"title": title, "page": page}

            response = request_api(url, params)
            raw = response.get("message", [])

            if not raw:
                break

            # clean keys
            books = [{k.strip(): v for k, v in b.items()} for b in raw]

            for b in books:
                if imported >= count:
                    break

                # ✅ SKIP duplicates by ISBN
                isbn = b.get("isbn", "")
                if isbn:
                    exists = Book.query.filter_by(isbn=isbn).first()
                    if exists:
                        continue

                new_book = Book(
                    title=b.get("title", ""),
                    author=b.get("authors", ""),
                    isbn=b.get("isbn", ""),
                    publisher=b.get("publisher", ""),
                    pages=int(b.get("num_pages") or 0),
                    stock=1
                )

                db.session.add(new_book)
                imported += 1

            db.session.commit()
            page += 1

        return redirect(url_for("books"))

    # initial GET request
    return render_template("import_books.html", preview=[])


if __name__ == "__main__":
    app.run(debug=True)
