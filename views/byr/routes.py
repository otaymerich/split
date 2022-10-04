from difflib import restore
from flask import Blueprint, render_template, request, session, url_for, redirect, make_response
from views.byr.models import db, Apartment, Roomie, Invoice, Debt
from secrets import token_urlsafe
import datetime as dt
from auth_obj  import Auth
from functools import reduce
import requests as req


byr = Blueprint("byr", __name__)
test_auth = Auth(session, Roomie, "byr.t_login", "byr.home",request, db)

@byr.route("/", methods=["GET", "POST"])
@test_auth.auth
def home():
    if session.get("apartment_id"):
        return redirect(url_for("byr.t_apartment"))
    return render_template("base.html")

@byr.route("/login", methods=["GET", "POST"])
@test_auth.login_check
def t_login():
    if request.method=="POST":
        name = request.form["name"]
        email = request.form["email"]
        pwd = Auth.encrypt_pwd(request.form["pwd"])
        date_start = dt.date.fromisoformat(request.form["checkin"])
        date_end = dt.date.fromisoformat(request.form["checkout"]) if request.form["checkout"] else None
        roomie = Roomie.add_roomie(name, email, pwd, date_start, date_end)
        db.session.add(roomie)
        db.session.commit()
    return render_template("login.html")
    

@byr.route("/apartment", methods=["GET", "POST"])
@test_auth.auth
def t_apartment():
    apartment = Apartment.query.filter_by(id=session.get("apartment_id")).first()
    if request.method=="POST":
        address = request.form["address"]
        rooms = request.form["rooms"]
        apartment = Apartment.add_apartment(address, rooms)
        db.session.add(apartment)
        db.session.commit()
        roomie = Roomie.query.filter_by(id=session["id"]).first()
        roomie.apartment_id = apartment.id
        session["apartment_id"] = roomie.apartment_id
        db.session.add(roomie)
        db.session.commit()
        return redirect(url_for("byr.home"))
    return render_template("apartment.html", apartment=apartment if apartment else None)

@byr.route("/logout")
def log_out():
    session.clear()
    res = make_response(redirect(url_for("byr.t_login")))
    res.delete_cookie("name")
    return res

@byr.route("/roomies", methods=["GET", "POST"])
@test_auth.auth
def t_roomies():
    if request.method=="POST":
        name = request.form["name"]
        email = request.form["email"]
        pwd = request.form["email"]
        date_start = dt.date.fromisoformat(request.form["checkin"])
        date_end = dt.date.fromisoformat(request.form["checkout"]) if request.form["checkout"] else None
        apartment_id = session["apartment_id"]
        roomie = Roomie.add_roomie(name, email, pwd, date_start, date_end, apartment_id)
        db.session.add(roomie)
        db.session.commit()
    apartment = Apartment.query.filter_by(id=session.get("apartment_id")).first()
    roomies = list(map(lambda roomie: roomie.public(), apartment.roomies))
    return render_template("roomies.html", elements=roomies, button_text = "Debts detail")

@test_auth.auth
@byr.route("/roomies/<roomie_id>", methods=["GET", "POST"])
def t_roomie_debt(roomie_id):
    roomie = Roomie.query.filter_by(id=roomie_id).first()
    elements=list(map(lambda debt: debt.public(), roomie.debts)) if len(roomie.debts) >= 0 else None
    return render_template("debts.html", elements=elements, button_text = "Pay!")


@test_auth.auth
@byr.route("/<roomie_id>/<debt_id>", methods=["GET", "POST"])
def t_pay_debt(roomie_id, debt_id):
    debt = Debt.query.filter_by(id=debt_id, roomie_id=roomie_id).first()
    debt.is_paid = True
    db.session.add(debt)
    roomie = Roomie.query.filter_by(id=roomie_id).first()
    roomie.debt -= debt.total
    db.session.add(roomie)
    db.session.commit()
    invoice = Invoice.query.filter_by(id=debt.invoice_id).first()
    inv_debts = invoice.debts
    is_paid = True
    for debt in inv_debts:
        is_paid = is_paid * debt.is_paid
    print(inv_debts)
    # is_paid = reduce(lambda debt1, debt2: debt1.is_paid * debt2.is_paid, inv_debts)
    if is_paid:
        invoice.is_paid = True
        db.session.add(invoice)
    db.session.commit()
    return redirect(f"/roomies/{roomie_id}")


@byr.route("/invoices", methods=["GET", "POST"])
@test_auth.auth
def t_invoices():
    apartment = Apartment.query.filter_by(id=session.get("apartment_id")).first()
    if request.method=="POST":
        form = dict(request.form)
        service = form.get("service")
        comment = form["comment"] if form["comment"] else None
        total = float(form.get("total"))
        date_start = dt.date.fromisoformat(form.get("start_date"))
        date_end = dt.date.fromisoformat(form.get("end_date"))
        is_paid = True if form.get("is_paid")=="on" else False
        apartment_id = session["apartment_id"]
        invoice = Invoice.add_invoice(apartment_id, service, total, date_start, date_end, comment, is_paid)
        for roomie in apartment.roomies:
            roomie.calculate_debt(apartment.rooms, invoice)
        db.session.add(invoice)
        db.session.commit()
    invoices = list(map(lambda invoice: invoice.public(), apartment.invoices))  
    if len(invoices)>0:
        return render_template("invoices.html", elements=invoices, button_text = "Pay!")
    return render_template("invoices.html")

@test_auth.auth
@byr.route("/invoices/<invoice_id>", methods=["GET", "POST"])
def t_pay_invoice(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id).first()
    invoice.is_paid = True
    db.session.add(invoice)
    inv_debts = invoice.debts
    for debt in inv_debts:
        roomie = Roomie.query.filter_by(id=debt.roomie_id).first()
        if not debt.is_paid:
            roomie.debt -= debt.total
            debt.is_paid = True
            db.session.add(roomie)
            db.session.add(debt)
    db.session.commit()
    return redirect(url_for("byr.t_invoices"))


@byr.route("/<e>")
def page_404(e):
    return redirect(url_for("byr.t_apartment"))

@byr.route("/test")
def t_test():
    # data = req.get("http://127.0.0.1:5000/api/apartments").json()
    # return data
    # roomie = Roomie.query.filter_by(id="10089d663258424eb72377254beb554b").first()
    # roomie.pwd = Auth.encrypt_pwd("1234Abcd")
    # db.session.add(roomie)
    # db.session.commit()
    return "test"