# Vehicle Service Mart

Python Flask + Bootstrap + MySQL project for vehicle service booking.

## Features

- Customer register/login/logout
- Service list: Oil Change, Repair, Wash, Full Service
- Customer booking create with vehicle number
- Server-side price calculation
- Future date/time validation
- Customer booking history with search/status filter
- Admin dashboard with reports
- Admin approve, complete, cancel, or reset booking status
- Admin booking search/filter by customer, vehicle, service, status, and date range

## Database

Default connection:

```text
Database: Vehicle_Booking_System
Username: root
Password: 0987654321
Host: localhost
```

The app creates the database, tables, services, and default admin account when it starts.

Default admin login:

```text
Email: admin@vehiclebooking.lk
Password: admin123
```

## Setup

Project structure:

```text
backend/   Flask backend, routes, MySQL connection, database script
frontend/  HTML templates, CSS, images
```

1. Install dependencies:

```bash
py -m pip install -r requirements.txt
```

2. Make sure MySQL Server is running.

3. Initialize the database:

```bash
py -m flask --app backend.app init-db
```

4. Run the project:

```bash
py -m flask --app backend.app run --debug
```

5. Open:

```text
http://127.0.0.1:5000
```

## Optional Environment Variables

You can override the default database settings:

```bash
set MYSQL_HOST=localhost
set MYSQL_USER=root
set MYSQL_PASSWORD=0987654321
set MYSQL_DATABASE=Vehicle_Booking_System
set SECRET_KEY=change-this-secret
```

## Manual Database Script

`backend/database.sql` is included if you want to create the database manually, but running the Flask app is enough.
