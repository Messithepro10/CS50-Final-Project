from flask import redirect, render_template, session
from functools import wraps
from cs50 import SQL
from datetime import datetime

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///bookings.db")

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"), ("&", "~a"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''"),]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def sgd(value):
    """Format value as SGD."""
    return f"${value:,.2f}"
