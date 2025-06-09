from flask import Flask, render_template, request, jsonify
import mysql.connector
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__, template_folder='templates')
print("Template folder path:", app.template_folder)

# MySQL database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',  # Replace with your MySQL username
    'password': 'your_password',  # Replace with your MySQL password
    'database': 'attendance_system'
}

def init_db():
    try:
        # First, connect without specifying a database to create the database
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        c = conn.cursor()
        c.execute("CREATE DATABASE IF NOT EXISTS attendance_system")
        conn.commit()
        conn.close()

        # Now connect to the database and create the table
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS students (
                     id INT PRIMARY KEY AUTO_INCREMENT,
                     name VARCHAR(255) NOT NULL,
                     email VARCHAR(255) NOT NULL,
                     total_classes INT,
                     attended_classes INT
                     )''')
        c.execute("INSERT INTO students (id, name, email, total_classes, attended_classes) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE name=name",
                  (1, "John Doe", "your_test_email@example.com", 100, 70))  # Replace with your email
        c.execute("INSERT INTO students (id, name, email, total_classes, attended_classes) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE name=name",
                  (2, "Jane Smith", "jane.smith@example.com", 100, 80))
        conn.commit()
        print("Database and table initialized successfully")
    except mysql.connector.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        conn.close()

def get_low_attendance_students():
    try:
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor()
        c.execute("SELECT id, name, email, total_classes, attended_classes FROM students WHERE (attended_classes * 100.0 / total_classes) < 75")
        students = c.fetchall()
        return [{"id": s[0], "name": s[1], "email": s[2], "percentage": (s[4] / s[3]) * 100} for s in students]
    except mysql.connector.Error as e:
        print(f"Error fetching students: {e}")
        return []
    finally:
        conn.close()

def send_email(student_name, student_email, percentage):
    sender_email = "your_email@gmail.com"  # Replace with your Gmail address
    sender_password = "your_app_password"  # Replace with your Gmail App Password
    subject = "Low Attendance Warning"
    body = f"""
    Dear {student_name},

    Your current attendance is {percentage:.2f}%, which is below the required 75%.
    If you do not improve your attendance, you may be exempted from writing the exams.

    Regards,
    Your Teacher
    """

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = student_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        print(f"Attempting to send email to {student_email}...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, student_email, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {student_email}")
        return True
    except Exception as e:
        print(f"Error sending email to {student_email}: {e}")
        return False

@app.route('/')
def index():
    students = get_low_attendance_students()
    return render_template('index.html', students=students)

@app.route('/send_email', methods=['POST'])
def send_email_route():
    print("Received request to send email...")
    student_id = request.json['student_id']
    print(f"Student ID: {student_id}")
    try:
        conn = mysql.connector.connect(**db_config)
        c = conn.cursor()
        c.execute("SELECT name, email, total_classes, attended_classes FROM students WHERE id = %s", (student_id,))
        student = c.fetchone()
        if student:
            name, email, total_classes, attended_classes = student
            percentage = (attended_classes / total_classes) * 100
            print(f"Student found: {name}, {email}, {percentage}%")
            if send_email(name, email, percentage):
                return jsonify({"status": "success", "message": f"Email sent to {name}"})
            else:
                return jsonify({"status": "error", "message": "Failed to send email"})
        return jsonify({"status": "error", "message": "Student not found"})
    except mysql.connector.Error as e:
        print(f"Error fetching student: {e}")
        return jsonify({"status": "error", "message": "Database error"})
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)