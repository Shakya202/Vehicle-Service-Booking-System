# Vehicle Service Booking System

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

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure MySQL Server is running.

3. Run the project:

```bash
py -m flask --app app run --debug
```

4. Open:

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

`database.sql` is included if you want to create the database manually, but running the Flask app is enough.
