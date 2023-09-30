from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, sgd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///bookings.db")

# Reset date and availability for facilities if it is new day
@app.before_first_request
def before_first_request():

    # Retrieve current date
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Retrieve date stored in database
    stored_date = db.execute("SELECT date FROM tt WHERE id = 1")

    # Reset date and availability for table tennis if it is new day
    if current_date != stored_date[0]["date"]:
        db.execute("UPDATE tt SET date = ?, availability = ?, user_id = NULL", datetime.now().strftime("%Y-%m-%d"), "Available")
        db.execute("UPDATE badminton SET date = ?, availability = ?, user_id = NULL", datetime.now().strftime("%Y-%m-%d"), "Available")
        db.execute("UPDATE gym SET date = ?, availability = ?, no_of_users = ?", datetime.now().strftime("%Y-%m-%d"), "Available", 0)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():

    # Load home page
    return render_template("index.html")


@app.route("/badminton")
@login_required
def badminton():
    """ Allows user to check details of badminton court"""

    # Load badminton availability page
    return render_template("badminton.html")


@app.route("/book")
@login_required
def book():
    """Allows user to book facilites"""

    # Load bookings page
    return render_template("book.html")


@app.route("/book_bmt", methods=["GET", "POST"])
@login_required
def book_badminton():
    """ Allows user to book badminton court"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Retrieve user's timeslot
        timeslot = request.form.get("timing")

        # Check if timeslot is valid
        if not timeslot:
            return apology("please select a valid timeslot", 400)

        # Check if timeslot has been booked
        status = db.execute("SELECT availability FROM badminton WHERE time = ?", timeslot)[0]["availability"]
        if status == "Booked":
            return apology("this timeslot has already been booked", 400)

        # Check if user has exceeded limit of 2 timeslots per day
        no_of_slots = db.execute("SELECT COUNT(id) AS no_of_slots FROM personal WHERE sport = ? AND date = ?", "Badminton", datetime.now().strftime("%Y-%m-%d"))[0]["no_of_slots"]
        if no_of_slots >= 2:
            return apology("each user is only limited to 2 time slots per day for each sport", 400)

        # Check if user has enough cash to book
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        if cash < 2:
            return apology("you do not have enough cash. please top up.", 400)

        # Update badminton table
        db.execute("UPDATE badminton SET user_id = ?, availability = ? WHERE time = ?", session["user_id"], "Booked", timeslot)

        # Insert new booking into bookings table
        db.execute("INSERT INTO bookings (sport, date, time, cost, user_id) VALUES (?, ?, ?, ?, ?)", "Badminton", datetime.now().strftime("%Y-%m-%d"), timeslot, 2.00, session["user_id"])

        # Insert new booking into personal table
        db.execute("INSERT INTO personal (sport, date, time, cost) VALUES (?, ?, ?, ?)", "Badminton", datetime.now().strftime("%Y-%m-%d"), timeslot, 2.00)

        # Update amount of cash in users table
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", 2.00, session["user_id"])

        # Retrieve user's bookings
        user_bookings = db.execute("SELECT sport, date, time, cost FROM personal ORDER BY date, time")

        # Format cost to 2 decimal places
        for booking in user_bookings:
            booking["cost"] = sgd(booking["cost"])

        # Load history page
        return render_template("history.html", user_bookings=user_bookings)

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Retrieve current availability for badminton
        bmt_availability = db.execute("SELECT time, availability FROM badminton")

        # Load badminton bookings page
        return render_template("book_bmt.html", bmt_availability = bmt_availability)


@app.route("/book_gym", methods=["GET", "POST"])
@login_required
def book_gym():
    """ Allows user to book gym"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Retrieve user's timeslot
        timeslot = request.form.get("timing")

        # Check if timeslot is valid
        if not timeslot:
            return apology("please select a valid timeslot", 400)

        # Check if timeslot has been booked by user
        gym_count = db.execute("SELECT COUNT(id) AS gym_count FROM personal WHERE date = ? AND time = ? AND sport = ?", datetime.now().strftime("%Y-%m-%d"), timeslot, "Gym")[0]["gym_count"]
        if gym_count >= 1:
            return apology("you have already booked this slot", 400)

        # Check if timeslot has been booked by others
        status = db.execute("SELECT availability FROM gym WHERE time = ?", timeslot)[0]["availability"]
        if status == "Booked":
            return apology("this timeslot has been fully booked", 400)

        # Check if user has exceeded limit of 2 timeslots per day
        no_of_slots = db.execute("SELECT COUNT(id) AS no_of_slots FROM personal WHERE sport = ? AND date = ?", "Gym", datetime.now().strftime("%Y-%m-%d"))[0]["no_of_slots"]
        if no_of_slots >= 2:
            return apology("each user is only limited to 2 time slots per day for each sport", 400)

        # Check if user has enough cash to book
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        if cash < 5:
            return apology("you do not have enough cash. please top up.", 400)

        # Update gym table
        db.execute("UPDATE gym SET no_of_users = no_of_users + 1 WHERE time = ?", timeslot)

        # Check if max occupancy has been reached
        no_of_users = db.execute("SELECT no_of_users FROM gym WHERE time = ?", timeslot)[0]["no_of_users"]
        if no_of_users == 5:
            db.execute("UPDATE gym SET availability = ? WHERE time = ?", "Booked", timeslot)

        # Insert new booking into bookings table
        db.execute("INSERT INTO bookings (sport, date, time, cost, user_id) VALUES (?, ?, ?, ?, ?)", "Gym", datetime.now().strftime("%Y-%m-%d"), timeslot, 5.00, session["user_id"])

        # Insert new booking into personal table
        db.execute("INSERT INTO personal (sport, date, time, cost) VALUES (?, ?, ?, ?)", "Gym", datetime.now().strftime("%Y-%m-%d"), timeslot, 5.00)

        # Update amount of cash in users table
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", 5.00, session["user_id"])

        # Retrieve user's bookings
        user_bookings = db.execute("SELECT sport, date, time, cost FROM personal ORDER BY date, time")

        # Format cost to 2 decimal places
        for booking in user_bookings:
            booking["cost"] = sgd(booking["cost"])

        # Load history page
        return render_template("history.html", user_bookings=user_bookings)

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Retrieve current availability for gym
        gym_availability = db.execute("SELECT time, availability, no_of_users FROM gym")

        # Load gym bookings page
        return render_template("book_gym.html", gym_availability = gym_availability)


@app.route("/book_tt", methods=["GET", "POST"])
@login_required
def book_tt():
    """ Allows user to book table tennis table"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Retrieve user's timeslot
        timeslot = request.form.get("timing")

        # Check if timeslot is valid
        if not timeslot:
            return apology("please select a valid timeslot", 400)

        # Check if timeslot has been booked
        status = db.execute("SELECT availability FROM tt WHERE time = ?", timeslot)[0]["availability"]
        if status == "Booked":
            return apology("this timeslot has already been booked", 400)

        # Check if user has exceeded limit of 2 timeslots per day
        no_of_slots = db.execute("SELECT COUNT(id) AS no_of_slots FROM personal WHERE sport = ? AND date = ?", "Table Tennis", datetime.now().strftime("%Y-%m-%d"))[0]["no_of_slots"]
        if no_of_slots >= 2:
            return apology("each user is only limited to 2 time slots per day for each sport", 400)

        # Check if user has enough cash to book
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        if cash < 1.5:
            return apology("you do not have enough cash. please top up.", 400)

        # Update tt table
        db.execute("UPDATE tt SET user_id = ?, availability = ? WHERE time = ?", session["user_id"], "Booked", timeslot)

        # Insert new booking into bookings table
        db.execute("INSERT INTO bookings (sport, date, time, cost, user_id) VALUES (?, ?, ?, ?, ?)", "Table Tennis", datetime.now().strftime("%Y-%m-%d"), timeslot, 1.50, session["user_id"])

        # Insert new booking into personal table
        db.execute("INSERT INTO personal (sport, date, time, cost) VALUES (?, ?, ?, ?)", "Table Tennis", datetime.now().strftime("%Y-%m-%d"), timeslot, 1.50)

        # Update amount of cash in users table
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", 1.50, session["user_id"])

        # Retrieve user's bookings
        user_bookings = db.execute("SELECT sport, date, time, cost FROM personal ORDER BY date, time")

        # Format cost to 2 decimal places
        for booking in user_bookings:
            booking["cost"] = sgd(booking["cost"])

        # Load history page
        return render_template("history.html", user_bookings=user_bookings)

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Retrieve current availability for table tennis
        tt_availability = db.execute("SELECT time, availability FROM tt")

        # Load table tennis bookings page
        return render_template("book_tt.html", tt_availability = tt_availability)


@app.route("/cash", methods=["GET", "POST"])
@login_required
def add_cash():
    """Allow user to add cash"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Retrieve amount of cash user has added
        cash = request.form.get("cash")

        # Update amount of cash in users table
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", cash, session["user_id"])

        # Retrieve user's total amount of cash
        total_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        total_cash = sgd(total_cash)

        # Reload cash page
        return render_template("cash.html", total_cash = total_cash)

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Retrieve user's total amount of cash
        total_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        total_cash = sgd(total_cash)

        # Load cash page
        return render_template("cash.html", total_cash = total_cash)


@app.route("/facilities")
@login_required
def facilities():
    """Allows user to check details of facilites"""

    # Load facilities page
    return render_template("facilities.html")


@app.route("/gym")
@login_required
def gym():
    """ Allows user to check details of gym"""

    # Load gym availability page
    return render_template("gym.html")


@app.route("/history")
@login_required
def history():
    """Displays table of user's bookings"""

    # Retrieve user's bookings
    user_bookings = db.execute("SELECT sport, date, time, cost FROM personal ORDER BY date, time")

    # Format cost to 2 decimal places
    for booking in user_bookings:
        booking["cost"] = sgd(booking["cost"])

    # Load history page
    return render_template("history.html", user_bookings=user_bookings)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Delete bookings of previous user
        db.execute("DELETE FROM personal")

        # Retrieve bookings of current user
        user_bookings = db.execute("SELECT sport, date, time, cost FROM bookings WHERE user_id = ?", session["user_id"])

        # Transfer bookings of current user into personal table
        for booking in user_bookings:
            db.execute("INSERT INTO personal (sport, date, time, cost) VALUES (?, ?, ?, ?)",
                        booking["sport"], booking["date"], booking["time"], booking["cost"])

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Retrieve username and password that user keyed in
        username = request.form.get("username")
        password = request.form.get("password")
        confirmed_pw = request.form.get("confirmation")
        hashed_pw = generate_password_hash(password)

        # Query database for username
        check_username = db.execute("SELECT username FROM users WHERE username = ?", username)

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 400)

        # Ensure username does not already exist
        elif check_username:
            return apology("username already exists", 400)

        # Ensure password was submitted
        elif (not password) or (not confirmed_pw):
            return apology("must provide password", 400)

        # Ensure password matches confirmed password
        elif password != confirmed_pw:
            return apology("passwords do not match", 400)

        # Register username and password of user into database
        registered_user_id = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hashed_pw)

        # Remember which user has logged in
        session["user_id"] = registered_user_id

        # Delete portfolio of previous user
        db.execute("DELETE FROM personal")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/tt")
@login_required
def table_tennis():
    """ Allows user to check details of table tennis table"""

    # Load table tennis availability page
    return render_template("table_tennis.html")
