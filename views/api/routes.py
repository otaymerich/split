from flask import Blueprint
from db import db
from views.byr.models import Apartment

api = Blueprint("api", __name__)

@api.route("/apartment")
def apartment():
    apartments = Apartment.query.all()
    apartments = list(map(lambda apartment: apartment.private(), apartments))
    data = {"succes": True, "data": apartments}
    return data

@api.route("/test")
def test():
    return "Test"