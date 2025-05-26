import os
import smtplib
import time
from datetime import datetime
from flask import session
from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user , login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey, Float
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import stripe

#=======================================================================================================================
app = Flask(__name__,static_folder="./static",template_folder="./templates")
YOUR_DOMAIN = 'http://localhost:4242'
load_dotenv()

stripe_api_key = os.getenv("STRIPE_API_KEY")
SECRET_KEY_ENV = os.getenv("SECRET_KEY")
EMAIL_ENV = os.getenv("EMAIL")
PASSWORD_ENV = os.getenv("PASSWORD")

app.config['SECRET_KEY'] = SECRET_KEY_ENV
app.config['UPLOAD_FOLDER'] = 'static/assets/img'
ckeditor = CKEditor(app)
Bootstrap5(app)
stripe.api_key = stripe_api_key

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///car_system.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)
#=======================================================================================================================

class User(UserMixin,db.Model):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    address: Mapped[Text] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(100), default="User", nullable=False)  #Enum("User", "Admin")
    sid: Mapped[str] = mapped_column(String(200), nullable=False)

    reservations = relationship("Reservation", back_populates="user")
    def get_id(self):
           return (self.user_id)
    def to_dict(self):
        dictionary = {}
        for column in self.__table__.columns:
            dictionary[column.name] = getattr(self, column.name)
        return dictionary



class Office(db.Model):
    __tablename__ = "office"
    office_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    office_country: Mapped[str] = mapped_column(String(100), nullable=False)
    office_location: Mapped[str] = mapped_column(String(300), nullable=False)

    cars = relationship("Car", back_populates="office")
    def to_dict(self):
        dictionary = {}
        for column in self.__table__.columns:
            dictionary[column.name] = getattr(self, column.name)
        return dictionary

class Car(db.Model):
    __tablename__ = "cars"
    car_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model: Mapped[str] = mapped_column(String(250), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    plate_id: Mapped[str] = mapped_column(String(100), unique=True)
    status: Mapped[str] = mapped_column(String(100))  #Enum("Available", "Not Available")
    office_id: Mapped[int] = mapped_column(Integer, ForeignKey("office.office_id"))
    image_url: Mapped[Text] = mapped_column(Text, nullable=False)
    car_price: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    seller_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.user_id"))

    office = relationship("Office", back_populates="cars")
    reservations = relationship("Reservation", back_populates="car")
    def to_dict(self):
        dictionary = {}
        for column in self.__table__.columns:
            dictionary[column.name] = getattr(self, column.name)
        return dictionary

class Reservation(db.Model):
    __tablename__ = "reservation"
    reservation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reservation_date: Mapped[str] = mapped_column(String(200), nullable=False)
    pickup_date: Mapped[str] = mapped_column(String(200), nullable=False)
    return_date: Mapped[str] = mapped_column(String(200), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(100), default="Not paid")  #Enum("Paid", "Not paid","Pay on site")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"))
    car_id: Mapped[int] = mapped_column(Integer, ForeignKey("cars.car_id"))

    user = relationship("User", back_populates="reservations")
    car = relationship("Car", back_populates="reservations")
    payments = relationship("Payment", back_populates="reservation")
    def to_dict(self):
        dictionary = {}
        for column in self.__table__.columns:
            dictionary[column.name] = getattr(self, column.name)
        return dictionary


class Payment(db.Model):
    __tablename__ = "payment"
    payment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_date: Mapped[str] = mapped_column(String(200))
    payment_amount: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(100), default="Cash", nullable=False)  #Enum("Cash", "VISA")
    reservation_id: Mapped[int] = mapped_column(Integer, ForeignKey("reservation.reservation_id"))

    reservation = relationship("Reservation", back_populates="payments")
    def to_dict(self):
        dictionary = {}
        for column in self.__table__.columns:
            dictionary[column.name] = getattr(self, column.name)
        return dictionary

with app.app_context():
    db.create_all()

with app.app_context():
    all_cars = db.session.query(Car).all()

class add_Form(FlaskForm):
    model = StringField('car model', validators=[DataRequired()])
    year = StringField('car year', validators=[DataRequired()])
    plate_id = StringField('car plate id', validators=[DataRequired()])
    status = SelectField('status', choices=['Available','Not Available'],validators=[DataRequired()])
    # office_id = StringField('office id', validators=[DataRequired()])
    office_id = SelectField('Office', coerce=int, validators=[DataRequired()])
    image_url = FileField("Upload Image",validators=[FileRequired(), FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    car_price = StringField('item price(USD)', validators=[DataRequired()])
    category = SelectField('category', choices=['Sedan','SUV','Coupe','Hatchback','Convertible','Wagon','Van','Truck'],validators=[DataRequired()])
    submit = SubmitField('Submit')

class add_office_Form(FlaskForm):
    office_country = StringField('office country', validators=[DataRequired()])
    office_location = StringField('office location', validators=[DataRequired()])
    submit = SubmitField('Submit')


class edit_Form(FlaskForm):
    model = StringField('car model', validators=[DataRequired()])
    year = StringField('car year', validators=[DataRequired()])
    plate_id = StringField('car plate id', validators=[DataRequired()])
    status = SelectField('status', choices=['Available', 'Not Available'], validators=[DataRequired()])
    office_id = SelectField('Office', coerce=int, validators=[DataRequired()])
    # office_id = StringField('office id', validators=[DataRequired()])
    image_url = FileField("Upload Image",validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    car_price = StringField('item price(USD)', validators=[DataRequired()])
    category = SelectField('category',choices=['Sedan', 'SUV', 'Coupe', 'Hatchback', 'Convertible', 'Wagon', 'Van', 'Truck'],validators=[DataRequired()])

    submit = SubmitField('Confirm Edit')

#=======================================================================================================================

@app.route("/")
def home():
    cars = jsonify([item.to_dict() for item in all_cars]).json[:6]
    return render_template("show.html",cars=cars)


@app.route("/all_cars")
def shop():
    cars = jsonify([car.to_dict() for car in all_cars]).json
    return render_template("index.html",cars=cars)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email_1"]
        password = request.form["password_1"]
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if not user:
            return render_template("login.html", alert="email doesn't exists!")
        elif not check_password_hash(user.password, password):
            return render_template("login.html", alert="Password incorrect, please try again.")
        else:
            login_user(user)
            return redirect(url_for('home'))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email_2"]
        username = request.form["username_2"]
        password = request.form["password_2"]
        role = "User"
        phone_number = request.form["phone_number"]
        address = request.form["address"]
        sid = request.form["sid"]
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user:
            return render_template("login.html", alert="User already exists!")
        hash_and_salted_password = generate_password_hash(password=password,method='pbkdf2:sha256',salt_length=8)
        new_user = User(username=username,email=email,password=hash_and_salted_password,phone_number = phone_number,address = address,role=role,sid=sid)
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return render_template("index.html")
        except Exception as e:
            db.session.rollback()
            print(f"Error occurred: {e}")
            return render_template("login.html", alert="An error occurred. Please try again.")
    return render_template("login.html")

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        msg = f'Subject:Thank you for reaching out to World Wheels, {request.form["name"]}!\n\n We have received your message:\n\n"{request.form["message"]}"\n\nOur team will review it and get back to you shortly.\n\nBest regards,\nThe World Wheels Team'
        send_email(request.form["email"], msg)
        return render_template("contact_us.html")
    return render_template("contact_us.html")

def send_email(email, message):
    EMAIL = EMAIL_ENV
    PASSWORD = PASSWORD_ENV
    with smtplib.SMTP("smtp.gmail.com",587) as connection:
        connection.starttls()
        connection.login(user=EMAIL,password=PASSWORD)
        connection.sendmail(from_addr=EMAIL,to_addrs= email,msg= message)


@app.route("/edit/<int:item_index>",methods=["POST","GET"])
def edit_car(item_index):
    car = Car.query.get(item_index)
    if car.seller_id != current_user.user_id:
        return jsonify({"error": "Unauthorized"}), 403
    form = edit_Form()
    i_url = car.image_url
    form.office_id.choices = [(office.office_id, f"{office.office_country} - {office.office_location}")
                              for office in db.session.query(Office).all()]
    if request.method == "GET":
        form.model.data = car.model
        form.year.data = car.year
        form.plate_id.data = car.plate_id
        form.category.data = car.category
        form.office_id.data = car.office_id
        form.car_price.data = car.car_price
        form.status.data = car.status
    elif form.validate_on_submit():
        car.model = form.model.data
        car.category = form.category.data
        car.car_price = form.car_price.data
        car.year = form.year.data
        car.plate_id = form.plate_id.data
        car.office_id = form.office_id.data
        car.status = form.status.data
        if form.image_url.data == None:
            car.image_url = i_url
        else:
            image_file = form.image_url.data
            image_filename = image_file.filename
            image_path_ = os.path.join(app.config['UPLOAD_FOLDER'], image_filename).replace("\\", "/")
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            image_file.save(image_path_)
            car.image_url = image_path_.replace("static/", "")
        db.session.commit()
        return redirect(url_for('my_shop'))
    return render_template("edit.html",form=form)




@app.route("/delete/<int:item_index>",methods=["POST"])
def delete_car(item_index):
    car = Car.query.get(item_index)
    if car.seller_id != current_user.user_id:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        db.session.delete(car)
        db.session.commit()
        return redirect(url_for('my_shop'))
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": {"message": str(e)}}), 500


@app.route("/my-shop")
def my_shop():
    print(all_cars)
    cars = jsonify([car.to_dict() for car in all_cars]).json
    seller_items = []
    for car in cars:
        if car['seller_id'] == current_user.user_id:
            seller_items.append(car)
    return render_template("my_shop.html",cars=seller_items)


@app.route("/my-rentals")
def my_rentals():
    reservations = db.session.query(Reservation).filter_by(user_id=current_user.user_id).all()
    print(reservations)
    if not reservations:
        return render_template("my_rented_cars.html", cars=[])
    cars_id = [reservation.car_id for reservation in reservations]
    cars = db.session.query(Car).filter(Car.car_id.in_(cars_id)).all()
    return render_template("my_rented_cars.html", cars=cars)



@app.route("/add-car", methods=["GET", "POST"])
def add_car():
    form = add_Form()
    form.office_id.choices = [(office.office_id, f"{office.office_country} - {office.office_location}")
                              for office in db.session.query(Office).all()]
    if form.validate_on_submit():
        image_file = form.image_url.data
        image_filename = image_file.filename
        image_path_ = os.path.join(app.config['UPLOAD_FOLDER'], image_filename).replace("\\","/")
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        image_file.save(image_path_)
        try:
            i = image_path_.replace("static/", "")
            new_item = Car(
                model=form.model.data,
                year=form.year.data,
                plate_id = form.plate_id.data,
                status=form.status.data,
                office_id = form.office_id.data,
                car_price=form.car_price.data,
                image_url=i,
                category=form.category.data,
                seller_id=current_user.user_id
            )
            db.session.add(new_item)
            db.session.commit()
            time.sleep(0.5)
            return redirect(url_for('my_shop'))
        except Exception as e:
            return jsonify({"error": {"message": str(e)}}), 500
    return render_template("add_car.html",form=form, current_user=current_user)





@app.route("/add-office", methods=["GET", "POST"])
def add_office():
    form = add_office_Form()
    if form.validate_on_submit():
        try:
            new_office = Office(
                office_country= form.office_country.data,
                office_location = form.office_location.data
            )
            db.session.add(new_office)
            db.session.commit()
            time.sleep(0.5)
            return redirect(url_for('home'))
        except Exception as e:
            return jsonify({"error": {"message": str(e)}}), 500
    return render_template("add_office.html",form=form, current_user=current_user)



@app.route("/rent/<int:item_index>",methods=["POST","GET"])
def rent_car(item_index):
    car = Car.query.get(item_index)
    if not car:
        return "Item not found", 404
    seller_name = db.session.query(User).filter_by(user_id=car.seller_id).first().to_dict()["username"]
    office_info = db.session.query(Office).filter_by(office_id=car.office_id).first().to_dict()
    location = f"{office_info['office_country']}-{office_info['office_location']}"
    if request.method == "POST":
        pd = request.form.get("pickup_date")
        rd = request.form.get("return_date")
        pickup_date = datetime.strptime(pd, '%Y-%m-%d').date()
        return_date = datetime.strptime(rd, '%Y-%m-%d').date()
        today = datetime.today().date()
        difference = (return_date - pickup_date)
        car_price = car.to_dict()['car_price']
        office_location = db.session.query(Office).filter_by(office_id=car.to_dict()['office_id']).first().office_location
        days = difference.days
        total = days * car_price
        payment_method = request.form.get("payment_method")
        if pickup_date < today or return_date < today :
            return jsonify({"error": "invalid date,pickup date or return date can't be in the past"}), 400
        elif pickup_date > return_date:
            return jsonify({"error": "invalid date,return date can't be before pickup date"}), 400
        else:
            session['car_info'] = {
                'car': car.to_dict(),
                'pickup_date': pickup_date,
                'return_date': return_date,
                'total': total,
                'payment_method': payment_method,
                'office_location':office_location
            }
            if payment_method == "visa":
               print("visa")
               return redirect(url_for('visa_checkout',total=total))
            elif payment_method == "cash":
                print("cash")
                return render_template("cash_checkout_confirmation.html",total=total,pickup_date= pickup_date,
                                                                                           return_date=return_date,
                                                                                           car=car.to_dict(),
                                                                                           payment_method = "cash")
    return render_template("rent.html",car=car,seller_name = seller_name,location=location)

@app.route('/visa_checkout/<int:total>', methods=["POST","GET"])
def visa_checkout(total):                #test visa:4242 4242 4242 4242
    print("visa_checkout")
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': 'USD',
                        'product_data': {
                            'name': 'Order Total',
                        },
                        'unit_amount': total*100,
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            success_url=url_for('confirm_stripe', _external=True),
            cancel_url=url_for('shop',alert="payment unsuccessful", _external=True)
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return str(e)


@app.route('/confirm_payment', methods=["POST","GET"])
def confirm_payment():
    car_info = session.get('car_info')
    if request.method == "GET":
        if not car_info:
            return jsonify({"error":"car info is missing"}),400
        result = car_info['car']['status']
        print(f'r = {result}')
        if result == "Not Available":
            return jsonify({"error": "car is unavailable"}), 400
        if car_info['payment_method'] == "cash":
            payment_status = "Pay on site"
            payment_method = "cash"
            reservation_process(car_info, payment_status, payment_method)
        elif car_info['payment_method'] == "visa":
            return redirect(url_for('visa_checkout',total=car_info["total"]))
        else:
            return jsonify({"error": "your purchase was declined"}), 400
    return redirect(url_for('shop'))


def reservation_process(car_info,payment_status,payment_method):
    print("sssssss")
    new_reservation = Reservation(reservation_date=datetime.today().date(), pickup_date=car_info['pickup_date'],return_date=car_info['return_date'], payment_status=payment_status,user_id=current_user.user_id, car_id=car_info['car']['car_id'])
    try:
        db.session.add(new_reservation)
        db.session.commit()
        check_reservation = db.session.query(Reservation).filter_by(reservation_id=new_reservation.reservation_id).first()
        if check_reservation:
            car = db.session.get(Car, car_info['car']['car_id'])
            print(car)
            car.status = "Not Available"
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print("3")
                return jsonify({"error": "An error occurred. Please try again."}), 400

            new_payment = Payment(payment_date=datetime.today().date(), payment_amount=car_info['total'],method=payment_method, reservation_id=new_reservation.reservation_id)
            try:
                db.session.add(new_payment)
                db.session.commit()
                msg = f"Subject:Thank you for your purchase at World Wheels,{current_user.username}!\n\n Your booking has been confirmed. If you have any questions, feel free to reach out to us.\n\nYour pickup location: {car_info['office_location']}\n\nBest regards,\nThe World Wheels Team"
                send_email(current_user.email, msg)
            except Exception as e:
                db.session.rollback()
                print("4")
                return jsonify({"error": "An error occurred. Please try again."}), 400
            return redirect(url_for('shop', alert="Payment successful"))
        else:
            print("5")
            return jsonify({"error": "reservation not found in database"}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error occurred: {e}")
        print("6")
        return jsonify({"error": "An error occurred. Please try again."}), 400




@app.route('/confirm-payment',methods=['GET','POST'])
def confirm_stripe():
    car_info = session.get('car_info')
    # result = db.session.execute(db.select(Reservation).where(Reservation.car_id == car_info["car"]["car_id"]))
    # reservation_duplicate = result.scalar()
    result = car_info['car']['status']
    if result == "Not Available":
        return jsonify({"error": "car is unavailable"}), 400
    print("confirm_stripe_1")
    if not car_info:
        return jsonify({"error": "car info is missing"}), 400
    return reservation_process(car_info,"Paid","visa")




@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        word = request.form["search"]
        print(word)
        cars = db.session.query(Car).filter(Car.model.ilike(f"%{word}%")).all()
        print(cars)
        return render_template("search.html",cars=cars)
    return render_template("home.html")


@app.route("/category/<string:category>")
def category_items(category):
    filtered_items = db.session.query(Car).filter_by(category=category).all()
    return render_template("category_items.html", cars=filtered_items)


if __name__ == '__main__':
     app.run(debug=True ,port=5006)
