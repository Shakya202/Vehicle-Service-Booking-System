import os
from datetime import date, datetime, time
from functools import wraps

import click
import mysql.connector
from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash


DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "0987654321"),
    "database": os.environ.get("MYSQL_DATABASE", "Vehicle_Booking_System"),
}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

SERVICE_SEED = [
    (
        "Oil Change",
        "Engine oil replacement, oil filter check, and basic fluid inspection.",
        6500.00,
        45,
    ),
    (
        "Repair",
        "General repair inspection and labour estimate for common vehicle issues.",
        12000.00,
        120,
    ),
    (
        "Wash",
        "Exterior wash, interior vacuum, tyre shine, and quick finishing.",
        3500.00,
        60,
    ),
    (
        "Full Service",
        "Complete inspection with oil, filters, wash, brake check, and diagnostics.",
        18500.00,
        180,
    ),
]

VALID_STATUSES = {"Pending", "Confirmed", "Completed", "Cancelled"}
WORK_START = time(8, 0)
WORK_END = time(17, 0)


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=os.path.join(FRONTEND_DIR, "static"),
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "vehicle-service-booking-dev-key"
    )

    register_cli(app)
    register_routes(app)
    ensure_database()
    with app.app_context():
        setup_schema()

    return app


def connect(include_database=True):
    config = DB_CONFIG.copy()
    if not include_database:
        config.pop("database", None)
    return mysql.connector.connect(**config)


def ensure_database():
    with connect(include_database=False) as db:
        cursor = db.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        db.commit()


def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db


def query_all(sql, params=()):
    cursor = get_db().cursor(dictionary=True)
    cursor.execute(sql, params)
    return cursor.fetchall()


def query_one(sql, params=()):
    cursor = get_db().cursor(dictionary=True)
    cursor.execute(sql, params)
    return cursor.fetchone()


def execute(sql, params=()):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(sql, params)
    db.commit()
    return cursor.lastrowid


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        if g.user["role"] != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return view(**kwargs)

    return wrapped_view


def validate_booking_date_time(booking_date, booking_time):
    if not booking_date or not booking_time:
        return "Please select booking date and time."

    try:
        selected_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
        selected_time = datetime.strptime(booking_time, "%H:%M").time()
    except ValueError:
        return "Invalid date or time format."

    selected_datetime = datetime.combine(selected_date, selected_time)
    if selected_datetime <= datetime.now():
        return "Booking date and time must be in the future."
    if selected_time < WORK_START or selected_time > WORK_END:
        return "Booking time must be between 08:00 AM and 05:00 PM."
    if selected_date.weekday() == 6:
        return "Bookings are not available on Sundays."
    return None


def normalize_vehicle_number(vehicle_number):
    return " ".join(vehicle_number.upper().split())


def calculate_price(service_id):
    service = query_one("SELECT base_price FROM services WHERE id = %s", (service_id,))
    return float(service["base_price"]) if service else None


def setup_schema():
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role ENUM('customer', 'admin') NOT NULL DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS services (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(80) NOT NULL UNIQUE,
            description TEXT NOT NULL,
            base_price DECIMAL(10,2) NOT NULL,
            duration_minutes INT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            service_id INT NOT NULL,
            vehicle_number VARCHAR(30) NOT NULL,
            booking_date DATE NOT NULL,
            booking_time TIME NOT NULL,
            total_price DECIMAL(10,2) NOT NULL,
            status ENUM('Pending', 'Confirmed', 'Completed', 'Cancelled')
                NOT NULL DEFAULT 'Pending',
            notes TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_bookings_user
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_bookings_service
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE RESTRICT,
            INDEX idx_bookings_status (status),
            INDEX idx_bookings_date (booking_date),
            INDEX idx_bookings_vehicle (vehicle_number)
        )
        """,
    ]

    db = get_db()
    cursor = db.cursor()
    for statement in statements:
        cursor.execute(statement)

    for name, description, price, duration in SERVICE_SEED:
        cursor.execute(
            """
            INSERT INTO services (name, description, base_price, duration_minutes)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                description = VALUES(description),
                base_price = VALUES(base_price),
                duration_minutes = VALUES(duration_minutes)
            """,
            (name, description, price, duration),
        )

    cursor.execute(
        """
        INSERT INTO users (name, email, password_hash, role)
        VALUES (%s, %s, %s, 'admin')
        ON DUPLICATE KEY UPDATE role = 'admin'
        """,
        (
            "System Admin",
            "admin@vehiclebooking.lk",
            generate_password_hash("admin123"),
        ),
    )
    db.commit()


def register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables and seed default data."""
        with app.app_context():
            ensure_database()
            setup_schema()
        click.echo("Database initialized: Vehicle_Booking_System")


def register_routes(app):
    @app.before_request
    def load_logged_in_user():
        g.user = None
        user_id = session.get("user_id")
        if user_id is not None:
            try:
                g.user = query_one("SELECT * FROM users WHERE id = %s", (user_id,))
            except Error:
                g.user = None

    @app.teardown_appcontext
    def close_db(error=None):
        db = g.pop("db", None)
        if db is not None and db.is_connected():
            db.close()

    @app.context_processor
    def inject_globals():
        return {
            "current_year": date.today().year,
            "valid_statuses": sorted(VALID_STATUSES),
        }

    @app.route("/")
    def index():
        if g.user:
            return redirect(url_for("dashboard"))
        services = query_all("SELECT * FROM services ORDER BY id")
        return render_template("index.html", services=services)

    @app.route("/register", methods=("GET", "POST"))
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            error = None
            if not name or not email or not password:
                error = "All fields are required."
            elif len(password) < 6:
                error = "Password must contain at least 6 characters."
            elif password != confirm_password:
                error = "Passwords do not match."
            elif query_one("SELECT id FROM users WHERE email = %s", (email,)):
                error = "This email is already registered."

            if error:
                flash(error, "danger")
            else:
                user_id = execute(
                    """
                    INSERT INTO users (name, email, password_hash, role)
                    VALUES (%s, %s, %s, 'customer')
                    """,
                    (name, email, generate_password_hash(password)),
                )
                session.clear()
                session["user_id"] = user_id
                flash("Registration successful. Welcome!", "success")
                return redirect(url_for("dashboard"))

        return render_template("register.html")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = query_one("SELECT * FROM users WHERE email = %s", (email,))

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "danger")
            else:
                session.clear()
                session["user_id"] = user["id"]
                flash("Login successful.", "success")
                return redirect(url_for("dashboard"))

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        if g.user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))

        bookings = query_all(
            """
            SELECT b.*, s.name AS service_name
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            WHERE b.user_id = %s
            ORDER BY b.booking_date DESC, b.booking_time DESC
            LIMIT 5
            """,
            (g.user["id"],),
        )
        services = query_all("SELECT * FROM services ORDER BY id")
        return render_template(
            "customer_dashboard.html", bookings=bookings, services=services
        )

    @app.route("/services")
    def services():
        services_list = query_all("SELECT * FROM services ORDER BY id")
        return render_template("services.html", services=services_list)

    @app.route("/bookings/new", methods=("GET", "POST"))
    @login_required
    def create_booking():
        if g.user["role"] == "admin":
            flash("Admins cannot create customer bookings.", "warning")
            return redirect(url_for("admin_dashboard"))

        services_list = query_all("SELECT * FROM services ORDER BY id")
        selected_service_id = request.args.get("service_id", type=int)

        if request.method == "POST":
            service_id = request.form.get("service_id", type=int)
            vehicle_number = normalize_vehicle_number(
                request.form.get("vehicle_number", "")
            )
            booking_date = request.form.get("booking_date", "")
            booking_time = request.form.get("booking_time", "")
            notes = request.form.get("notes", "").strip()
            total_price = calculate_price(service_id)

            error = None
            if not service_id or total_price is None:
                error = "Please select a valid service."
            elif not vehicle_number:
                error = "Vehicle number is required."
            elif len(vehicle_number) < 3:
                error = "Vehicle number is too short."
            else:
                error = validate_booking_date_time(booking_date, booking_time)

            if error:
                flash(error, "danger")
                selected_service_id = service_id
            else:
                execute(
                    """
                    INSERT INTO bookings
                        (user_id, service_id, vehicle_number, booking_date,
                         booking_time, total_price, status, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, 'Pending', %s)
                    """,
                    (
                        g.user["id"],
                        service_id,
                        vehicle_number,
                        booking_date,
                        booking_time,
                        total_price,
                        notes or None,
                    ),
                )
                flash("Booking created successfully. Status: Pending.", "success")
                return redirect(url_for("booking_history"))

        return render_template(
            "booking_form.html",
            services=services_list,
            selected_service_id=selected_service_id,
            today=date.today().isoformat(),
        )

    @app.route("/bookings")
    @login_required
    def booking_history():
        if g.user["role"] == "admin":
            return redirect(url_for("admin_bookings"))

        status = request.args.get("status", "")
        search = request.args.get("search", "").strip()
        params = [g.user["id"]]
        filters = ["b.user_id = %s"]

        if status in VALID_STATUSES:
            filters.append("b.status = %s")
            params.append(status)
        if search:
            filters.append("(b.vehicle_number LIKE %s OR s.name LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        bookings = query_all(
            f"""
            SELECT b.*, s.name AS service_name
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            WHERE {' AND '.join(filters)}
            ORDER BY b.booking_date DESC, b.booking_time DESC
            """,
            tuple(params),
        )
        return render_template(
            "booking_history.html",
            bookings=bookings,
            selected_status=status,
            search=search,
        )

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        stats = {
            "total": query_one("SELECT COUNT(*) AS value FROM bookings")["value"],
            "pending": query_one(
                "SELECT COUNT(*) AS value FROM bookings WHERE status = 'Pending'"
            )["value"],
            "confirmed": query_one(
                "SELECT COUNT(*) AS value FROM bookings WHERE status = 'Confirmed'"
            )["value"],
            "completed": query_one(
                "SELECT COUNT(*) AS value FROM bookings WHERE status = 'Completed'"
            )["value"],
            "cancelled": query_one(
                "SELECT COUNT(*) AS value FROM bookings WHERE status = 'Cancelled'"
            )["value"],
            "revenue": query_one(
                """
                SELECT COALESCE(SUM(total_price), 0) AS value
                FROM bookings
                WHERE status = 'Completed'
                """
            )["value"],
        }
        service_report = query_all(
            """
            SELECT s.name, COUNT(b.id) AS booking_count,
                   COALESCE(SUM(CASE WHEN b.status = 'Completed'
                                      THEN b.total_price ELSE 0 END), 0) AS revenue
            FROM services s
            LEFT JOIN bookings b ON b.service_id = s.id
            GROUP BY s.id, s.name
            ORDER BY booking_count DESC, s.name
            """
        )
        recent_bookings = query_all(
            """
            SELECT b.*, s.name AS service_name, u.name AS customer_name
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            JOIN users u ON u.id = b.user_id
            ORDER BY b.created_at DESC
            LIMIT 8
            """
        )
        return render_template(
            "admin_dashboard.html",
            stats=stats,
            service_report=service_report,
            recent_bookings=recent_bookings,
        )

    @app.route("/admin/bookings")
    @admin_required
    def admin_bookings():
        status = request.args.get("status", "")
        service_id = request.args.get("service_id", type=int)
        search = request.args.get("search", "").strip()
        date_from = request.args.get("date_from", "")
        date_to = request.args.get("date_to", "")

        filters = []
        params = []
        if status in VALID_STATUSES:
            filters.append("b.status = %s")
            params.append(status)
        if service_id:
            filters.append("b.service_id = %s")
            params.append(service_id)
        if search:
            filters.append(
                "(u.name LIKE %s OR u.email LIKE %s OR b.vehicle_number LIKE %s)"
            )
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        if date_from:
            filters.append("b.booking_date >= %s")
            params.append(date_from)
        if date_to:
            filters.append("b.booking_date <= %s")
            params.append(date_to)

        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
        bookings = query_all(
            f"""
            SELECT b.*, s.name AS service_name, u.name AS customer_name, u.email
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            JOIN users u ON u.id = b.user_id
            {where_sql}
            ORDER BY b.booking_date DESC, b.booking_time DESC
            """,
            tuple(params),
        )
        services_list = query_all("SELECT * FROM services ORDER BY id")
        return render_template(
            "admin_bookings.html",
            bookings=bookings,
            services=services_list,
            filters={
                "status": status,
                "service_id": service_id,
                "search": search,
                "date_from": date_from,
                "date_to": date_to,
            },
        )

    @app.post("/admin/bookings/<int:booking_id>/status")
    @admin_required
    def update_booking_status(booking_id):
        new_status = request.form.get("status")
        if new_status not in VALID_STATUSES:
            flash("Invalid booking status.", "danger")
            return redirect(url_for("admin_bookings"))

        booking = query_one("SELECT * FROM bookings WHERE id = %s", (booking_id,))
        if booking is None:
            flash("Booking not found.", "danger")
            return redirect(url_for("admin_bookings"))

        execute(
            "UPDATE bookings SET status = %s WHERE id = %s",
            (new_status, booking_id),
        )
        flash(f"Booking #{booking_id} marked as {new_status}.", "success")
        return redirect(request.referrer or url_for("admin_bookings"))


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
