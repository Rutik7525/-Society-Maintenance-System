# Society Maintenance System

📄 Project Overview

The Society Maintenance System is a web-based application developed to help housing societies streamline the management of maintenance billing, payments, and receipts. The system allows users (residents) to log in, view their maintenance charges, pay their dues online, and download receipts. Admin users can monitor payments and update billing information. The system reduces manual work, increases transparency, and improves efficiency in society operations.

🧑‍💻 Technical Description

✅ Frontend
Languages: HTML, CSS

Templates: Jinja2 (used within Flask)

Features: Forms for login/payment, responsive user interface, receipt generation page.

✅ Backend
Language: Python

Framework: Flask

Database: SQLite

File: app.py (contains routes, database connections, logic)

✅ Database
File: schema.sql

Contains tables for:

users: User credentials and roles

payments: Records of payment transactions

receipts: Receipt file references and status

🔐 Modules and Functionalities
👤 User Module
Login authentication using username and password

View pending maintenance bills

Generate and pay bills online

Download PDF receipts for paid bills

🛠️ Admin Module
Admin login dashboard

Add or update maintenance bills for each flat

View payment history of all users

Manage receipt templates (PDFs, QR codes)

📤 Receipt Generator
Auto-generates PDF receipts using user and payment data

Includes QR code for digital verification

🧪 Testing and Deployment
Tested on local server using Flask’s development server

Can be deployed to Heroku, PythonAnywhere, or any cloud that supports Python apps

📂 Directory Structure (Main Files)
app.py: Main Flask application

schema.sql: SQL script to create tables

templates/index.html: Main page template

static/: Stores QR codes and receipt PDFs

.env.txt: Contains environment variables
