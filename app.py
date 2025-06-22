from flask import Flask, request, jsonify, render_template, send_file, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import calendar
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import qrcode
import io
from PIL import Image
import tempfile
import subprocess

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', '134e4f1e34170d1bfb1cc0055c35daf9714694f0e8704d65')
load_dotenv()

# MySQL Configuration
db_config = {
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', '@Ritik7525'),
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'database': os.getenv('MYSQL_DATABASE', 'updated_society_maintenance')
}

# Email Configuration
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'ritikjagde@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'Ritikadmin75')

# UPI Configuration
UPI_ID = os.getenv('UPI_ID', 'guruchougule3@oksbi')

# Initialize Database
def init_db():
    conn = None
    c = None
    try:
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor(buffered=True)
        print("Initializing database...")
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password TEXT,
            wing VARCHAR(10),
            role VARCHAR(10),
            email VARCHAR(100)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS bills (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            month VARCHAR(7),
            amount DECIMAL(10,2),
            status VARCHAR(10),
            due_date VARCHAR(10),
            maintenance DECIMAL(10,2),
            water DECIMAL(10,2),
            security DECIMAL(10,2),
            sinking_fund DECIMAL(10,2),
            FOREIGN KEY(user_id) REFERENCES users(id),
            UNIQUE(user_id, month)
        )''')
        
        admin_password = generate_password_hash('admin123')
        c.execute('INSERT IGNORE INTO users (username, password, wing, role, email) VALUES (%s, %s, %s, %s, %s)',
                  ('admin', admin_password, '', 'admin', 'admin@example.com'))
        
        for wing in ['A', 'B']:
            for i in range(1, 11):
                username = f'wing{wing}{i}'
                password = generate_password_hash('password')
                email = f'{username}@example.com'
                c.execute('INSERT IGNORE INTO users (username, password, wing, role, email) VALUES (%s, %s, %s, %s, %s)',
                          (username, password, wing, 'user', email))
        
        conn.commit()
        print("Database initialized successfully.")
    except mysql.connector.Error as e:
        print(f"Database initialization failed: {e}")
    finally:
        if c is not None:
            c.close()
        if conn is not None:
            conn.close()

# Send Email Notification
def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Email sending failed to {to_email}: {e}")

# Auto-generate Bills for a Specific Month
def generate_bills(target_month=None):
    conn = None
    c = None
    try:
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor(buffered=True)
        current_month = target_month if target_month else session.get('current_month', datetime.datetime.now().strftime('%Y-%m'))
        print(f"Target month for bill generation: {current_month}")
        
        if current_month == '2025-05':
            year, month = 2025, 5
        else:
            year, month = map(int, current_month.split('-'))
        
        last_day = calendar.monthrange(year, month)[1]
        due_date = f'{current_month}-{last_day}'
        print(f"Generating bills for {current_month}, due date: {due_date}...")
        
        c.execute('SELECT id, username, email FROM users WHERE role = "user"')
        users = c.fetchall()
        print(f"Found {len(users)} users: {[user[1] for user in users]}")
        
        admin_summary = f"Bill Generation Summary for {current_month}:\n\n"
        for user_id, username, email in users:
            print(f"Checking bill for {username} (user_id: {user_id})...")
            c.execute('SELECT id FROM bills WHERE user_id = %s AND month = %s', (user_id, current_month))
            existing_bill = c.fetchone()
            if not existing_bill:
                maintenance = 800.00
                water = 300.00
                security = 300.00
                sinking_fund = 100.00
                amount = maintenance + water + security + sinking_fund
                print(f"Inserting bill for {username}: user_id={user_id}, month={current_month}, amount=₹{amount}")
                c.execute('''INSERT INTO bills (user_id, month, amount, status, due_date, maintenance, water, security, sinking_fund)
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                          (user_id, current_month, amount, 'Pending', due_date, maintenance, water, security, sinking_fund))
                c.execute('SELECT LAST_INSERT_ID()')
                bill_id = c.fetchone()[0]
                print(f"Bill inserted successfully for {username}, bill_id: {bill_id}")
                body = f"""Dear {username},\n\nYour maintenance bill for {current_month} has been generated:\n
Amount: ₹{amount}\nDue Date: {due_date}\nStatus: Pending\n
Breakdown:\n- Maintenance: ₹{maintenance}\n- Water: ₹{water}\n- Security: ₹{security}\n- Sinking Fund: ₹{sinking_fund}\n
Please log in to view the QR code for payment via UPI.\n\nRegards,\nSociety Maintenance System"""
                send_email(email, f'Maintenance Bill for {current_month}', body)
                admin_summary += f"- {username}: ₹{amount} (Pending)\n"
            else:
                print(f"Bill already exists for {username} (bill_id: {existing_bill[0]}).")
        
        conn.commit()
        print("Bill generation completed, committing changes.")
        
        c.execute('SELECT email FROM users WHERE role = "admin"')
        admin_email = c.fetchone()[0]
        send_email(admin_email, f'Bill Generation Summary {current_month}', admin_summary)
        print("Admin summary email sent.")
    except mysql.connector.Error as e:
        print(f"Bill generation failed due to database error: {e}")
        if conn:
            conn.rollback()
            print("Rolled back database changes due to error.")
    except Exception as e:
        print(f"Bill generation failed due to unexpected error: {e}")
        if conn:
            conn.rollback()
            print("Rolled back database changes due to error.")
    finally:
        if c is not None:
            c.close()
        if conn is not None:
            conn.close()
        print("Database connection closed.")

# Create Custom Bill with Breakdown
@app.route('/create_custom_bill', methods=['POST'])
def create_custom_bill():
    data = request.json
    username = data['username']
    month = data['month']
    maintenance = float(data['breakdown']['maintenance'])
    water = float(data['breakdown']['water'])
    security = float(data['breakdown']['security'])
    sinking_fund = float(data['breakdown']['sinking_fund'])
    amount = maintenance + water + security + sinking_fund
    
    try:
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor(buffered=True)
        print(f"Creating custom bill for {username}, month {month}, amount ₹{amount}...")
        
        c.execute('SELECT id, email FROM users WHERE username = %s', (username,))
        user = c.fetchone()
        if not user:
            print(f"User {username} not found.")
            conn.close()
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        user_id, email = user
        last_day = calendar.monthrange(int(month[:4]), int(month[5:]))[1]
        due_date = f'{month}-{last_day}'
        
        c.execute('SELECT id FROM bills WHERE user_id = %s AND month = %s', (user_id, month))
        existing_bill = c.fetchone()
        if existing_bill:
            print(f"Bill already exists for {username}, month {month}. Updating existing bill...")
            c.execute('''UPDATE bills SET amount = %s, status = %s, due_date = %s, maintenance = %s, water = %s, security = %s, sinking_fund = %s
                         WHERE user_id = %s AND month = %s''',
                      (amount, 'Pending', due_date, maintenance, water, security, sinking_fund, user_id, month))
        else:
            c.execute('''INSERT INTO bills (user_id, month, amount, status, due_date, maintenance, water, security, sinking_fund)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                      (user_id, month, amount, 'Pending', due_date, maintenance, water, security, sinking_fund))
            print(f"Custom bill created for {username}: ₹{amount}")
        
        conn.commit()
        
        session['current_month'] = month
        print(f"Set current_month to {month} in session.")
        
        body = f"""Dear {username},\n\nYour maintenance bill for {month} has been generated:\n
Amount: ₹{amount}\nDue Date: {due_date}\nStatus: Pending\n
Breakdown:\n- Maintenance: ₹{maintenance}\n- Water: ₹{water}\n- Security: ₹{security}\n- Sinking Fund: ₹{sinking_fund}\n
Please log in to view the QR code for payment via UPI.\n\nRegards,\nSociety Maintenance System"""
        send_email(email, f'Maintenance Bill for {month}', body)
        
        c.execute('SELECT email FROM users WHERE role = "admin"')
        admin_email = c.fetchone()[0]
        send_email(admin_email, f'Custom Bill Created for {username}', 
                   f"Custom bill for {username} ({month}): ₹{amount}, Due: {due_date}\n"
                   f"Breakdown:\n- Maintenance: ₹{maintenance}\n- Water: ₹{water}\n- Security: ₹{security}\n- Sinking Fund: ₹{sinking_fund}")
        
        conn.close()
        return jsonify({'success': True})
    except mysql.connector.Error as e:
        print(f"Creating custom bill failed: {e}")
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    password = data['password']
    
    try:
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor(buffered=True)
        print(f"Attempting login for {username}...")
        c.execute('SELECT password, role FROM users WHERE username = %s', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[0], password):
            print(f"Login successful for {username}. Generating bills...")
            session['current_month'] = '2025-05'
            generate_bills(target_month='2025-05')
            return jsonify({'success': True, 'role': user[1]})
        print(f"Login failed for {username}.")
        return jsonify({'success': False})
    except mysql.connector.Error as e:
        print(f"Login failed: {e}")
        return jsonify({'success': False})

@app.route('/bills', methods=['GET'])
def get_bills():
    try:
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor(buffered=True)
        current_month = session.get('current_month', datetime.datetime.now().strftime('%Y-%m'))
        print(f"Fetching bills for month {current_month}...")
        c.execute('''SELECT b.id, b.user_id, u.username, u.wing, b.month, b.amount, b.status, b.maintenance, b.water, b.security, b.sinking_fund
                     FROM bills b JOIN users u ON b.user_id = u.id WHERE b.month = %s''', (current_month,))
        bills = [{
            'id': row[0],
            'user_id': row[1],
            'username': row[2],
            'wing': row[3],
            'month': row[4],
            'amount': float(row[5]),
            'status': row[6],
            'breakdown': {
                'maintenance': float(row[7]),
                'water': float(row[8]),
                'security': float(row[9]),
                'sinking_fund': float(row[10])
            }
        } for row in c.fetchall()]
        conn.close()
        print(f"Fetched {len(bills)} bills for {current_month}.")
        return jsonify(bills)
    except mysql.connector.Error as e:
        print(f"Fetching bills failed: {e}")
        return jsonify({'error': 'Failed to fetch bills'}), 500

@app.route('/bills/<username>', methods=['GET'])
def get_user_bills(username):
    try:
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor(buffered=True)
        current_month = session.get('current_month', datetime.datetime.now().strftime('%Y-%m'))
        print(f"Fetching bills for {username}, month {current_month}...")
        c.execute('''SELECT b.id, b.month, b.amount, b.status, b.maintenance, b.water, b.security, b.sinking_fund
                     FROM bills b JOIN users u ON b.user_id = u.id 
                     WHERE u.username = %s AND b.month = %s
                     LIMIT 1''',
                     (username, current_month))
        bills = [{
            'id': row[0],
            'month': row[1],
            'amount': float(row[2]),
            'status': row[3],
            'breakdown': {
                'maintenance': float(row[4]),
                'water': float(row[5]),
                'security': float(row[6]),
                'sinking_fund': float(row[7])
            }
        } for row in c.fetchall()]
        conn.close()
        print(f"Fetched {len(bills)} bills for {username}, {current_month}.")
        return jsonify(bills)
    except mysql.connector.Error as e:
        print(f"Fetching user bills failed: {e}")
        return jsonify({'error': 'Failed to fetch user bills'}), 500

@app.route('/edit_bill', methods=['POST'])
def edit_bill():
    data = request.json
    try:
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor(buffered=True)
        print(f"Editing bill ID {data['id']}...")
        amount = float(data['breakdown']['maintenance']) + float(data['breakdown']['water']) + \
                 float(data['breakdown']['security']) + float(data['breakdown']['sinking_fund'])
        c.execute('''UPDATE bills SET amount = %s, status = %s, maintenance = %s, water = %s, security = %s, sinking_fund = %s
                     WHERE id = %s''', (amount, data['status'], data['breakdown']['maintenance'],
                                        data['breakdown']['water'], data['breakdown']['security'],
                                        data['breakdown']['sinking_fund'], data['id']))
        conn.commit()
        conn.close()
        print(f"Bill edited successfully. New amount: ₹{amount}")
        return jsonify({'success': True, 'new_amount': amount})
    except mysql.connector.Error as e:
        print(f"Editing bill failed: {e}")
        return jsonify({'success': False}), 500

@app.route('/qr_code/<int:bill_id>', methods=['GET'])
def get_qr_code(bill_id):
    conn = None
    try:
        print(f"Attempting to generate QR code for bill ID {bill_id}...")
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor(buffered=True)
        print(f"Executing query to fetch bill data for bill ID {bill_id}...")
        c.execute('''SELECT b.amount, b.month, u.username
                     FROM bills b JOIN users u ON b.user_id = u.id WHERE b.id = %s''', (bill_id,))
        bill = c.fetchone()
        print(f"Query result: {bill}")
        
        if not bill:
            print(f"Bill ID {bill_id} not found in the database.")
            return jsonify({'error': f'Bill ID {bill_id} not found'}), 404
        
        amount, month, username = bill
        print(f"Bill found: amount=₹{amount}, month={month}, username={username}")
        
        upi_link = f"upi://pay?pa={UPI_ID}&pn=Society&am={amount}&cu=INR&tn=Bill_{username}_{month}"
        print(f"Generated UPI link: {upi_link}")
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(upi_link)
        qr.make(fit=True)
        print("QR code object created and data added.")
        
        img = qr.make_image(fill='black', back_color='white')
        print("QR code image generated.")
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        print(f"QR code image saved to byte array for {username}, {month}, ₹{amount}.")
        
        response = send_file(img_byte_arr, mimetype='image/png', as_attachment=True, download_name=f'bill_{month}.png')
        print(f"QR code response sent for bill ID {bill_id}.")
        return response
    except mysql.connector.Error as e:
        print(f"Database error while generating QR code for bill ID {bill_id}: {e}")
        return jsonify({'error': f'Database error while generating QR code: {str(e)}'}), 500
    except Exception as e:
        print(f"Unexpected error while generating QR code for bill ID {bill_id}: {e}")
        return jsonify({'error': f'Failed to generate QR code due to an unexpected error: {str(e)}'}), 500
    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")

@app.route('/generate_bill_receipt/<int:bill_id>', methods=['GET'])
def generate_bill_receipt(bill_id):
    conn = None
    tex_file_path = None
    pdf_file_path = None
    try:
        print(f"Generating bill receipt for bill ID {bill_id}...")
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor(buffered=True)
        c.execute('''SELECT b.amount, b.month, b.due_date, b.status, b.maintenance, b.water, b.security, b.sinking_fund, u.username, u.wing
                     FROM bills b JOIN users u ON b.user_id = u.id WHERE b.id = %s''', (bill_id,))
        bill = c.fetchone()
        
        if not bill:
            print(f"Bill ID {bill_id} not found.")
            return jsonify({'error': f'Bill ID {bill_id} not found'}), 404

        if bill[3] != 'Paid':
            print(f"Bill ID {bill_id} is not paid.")
            return jsonify({'error': 'Bill is not paid. Receipt can only be generated for paid bills.'}), 400

        amount, month, due_date, status, maintenance, water, security, sinking_fund, username, wing = bill
        print(f"Bill details: username={username}, month={month}, amount=₹{amount}, status={status}")

        # Creating LaTeX document for receipt
        latex_content = r'''
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{geometry}
\geometry{margin=2cm}
\usepackage{booktabs}
\usepackage{parskip}
\usepackage{xcolor}
\usepackage{titlesec}

\titleformat{\section}{\large\bfseries\color{blue}}{\thesection}{1em}{}
\titleformat{\subsection}{\bfseries}{\thesubsection}{1em}{}

\begin{document}

\begin{center}
    {\LARGE\bfseries Society Maintenance Bill Receipt}\\[0.5cm]
    {\large Society Name: Harmony Residency}\\[0.2cm]
    {\large Date: ''' + datetime.datetime.now().strftime('%Y-%m-%d') + r'''}
\end{center}

\section*{Resident Details}
\begin{tabular}{ll}
    \textbf{Name:} & ''' + username + r''' \\
    \textbf{Wing:} & ''' + wing + r''' \\
    \textbf{Bill Month:} & ''' + month + r''' \\
    \textbf{Due Date:} & ''' + due_date + r''' \\
\end{tabular}

\section*{Payment Details}
\begin{tabular}{lr}
    \toprule
    \textbf{Description} & \textbf{Amount (₹)} \\
    \midrule
    Maintenance & ''' + f"{maintenance:.2f}" + r''' \\
    Water & ''' + f"{water:.2f}" + r''' \\
    Security & ''' + f"{security:.2f}" + r''' \\
    Sinking Fund & ''' + f"{sinking_fund:.2f}" + r''' \\
    \midrule
    \textbf{Total Amount} & ''' + f"{amount:.2f}" + r''' \\
    \bottomrule
\end{tabular}

\section*{Payment Status}
\textbf{Status:} Paid \\
\textbf{Payment Date:} ''' + datetime.datetime.now().strftime('%Y-%m-%d') + r'''

\begin{center}
    \textit{Thank you for your payment. This is an auto-generated receipt.}
\end{center}

\end{document}
'''

        # Writing LaTeX content to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.tex', delete=False, mode='w', encoding='utf-8') as tex_file:
            tex_file.write(latex_content)
            tex_file_path = tex_file.name
        print(f"LaTeX file created at {tex_file_path}")

        # Compiling LaTeX to PDF using pdflatex
        output_dir = tempfile.gettempdir()
        pdf_file_path = os.path.join(output_dir, f'receipt_{bill_id}.pdf')
        try:
            result = subprocess.run(
                ['pdflatex', '-output-directory', output_dir, tex_file_path],
                check=True, capture_output=True, text=True
            )
            print(f"PDF generated at {pdf_file_path}: {result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"LaTeX compilation failed: {e.stderr}")
            return jsonify({'error': f'Failed to generate PDF receipt: {e.stderr}'}), 500
        except FileNotFoundError:
            print("pdflatex not found. Ensure TeX Live is installed.")
            return jsonify({'error': 'pdflatex not found. Please install TeX Live.'}), 500

        # Sending the PDF file
        response = send_file(
            pdf_file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'receipt_{username}_{month}.pdf'
        )
        print(f"Receipt PDF sent for bill ID {bill_id}.")
        return response

    except mysql.connector.Error as e:
        print(f"Database error while generating receipt for bill ID {bill_id}: {e}")
        return jsonify({'error': f'Database error while generating receipt: {str(e)}'}), 500
    except Exception as e:
        print(f"Unexpected error while generating receipt for bill ID {bill_id}: {e}")
        return jsonify({'error': f'Failed to generate receipt due to an unexpected error: {str(e)}'}), 500
    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")
        if tex_file_path and os.path.exists(tex_file_path):
            try:
                os.unlink(tex_file_path)
                print(f"Cleaned up LaTeX file {tex_file_path}")
            except Exception as e:
                print(f"Failed to clean up LaTeX file {tex_file_path}: {e}")
        if pdf_file_path and os.path.exists(pdf_file_path):
            try:
                os.unlink(pdf_file_path)
                print(f"Cleaned up PDF file {pdf_file_path}")
            except Exception as e:
                print(f"Failed to clean up PDF file {pdf_file_path}: {e}")

if __name__ == '__main__':
    print("Starting Flask application...")
    init_db()
    app.run(debug=True)