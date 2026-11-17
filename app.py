
from flask import Flask, render_template, request, redirect, jsonify, Response
import sqlite3
import os
import base64
import re
import subprocess
import sys
import csv
import io

app = Flask(__name__)


# ==========================================
# HOME / DASHBOARD
# ==========================================

@app.route("/")
def home():
    connection = sqlite3.connect("attendance.db")
    cursor = connection.cursor()

    # Total registered students
    cursor.execute("""
        SELECT COUNT(*)
        FROM students
    """)
    total_students = cursor.fetchone()[0]

    # Students present today
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE date = date('now', 'localtime')
    """)
    present_today = cursor.fetchone()[0]

    # Total attendance records
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
    """)
    total_records = cursor.fetchone()[0]

    # Recent attendance
    cursor.execute("""
        SELECT student_id, date, time, status
        FROM attendance
        ORDER BY date DESC, time DESC
        LIMIT 5
    """)
    recent_records = cursor.fetchall()

    connection.close()

    return render_template(
        "index.html",
        total_students=total_students,
        present_today=present_today,
        total_records=total_records,
        recent_records=recent_records
    )


# ==========================================
# REGISTER STUDENT
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        student_id = request.form["student_id"]
        student_name = request.form["student_name"]

        connection = sqlite3.connect("attendance.db")
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO students
                (student_id, name)
                VALUES (?, ?)
                """,
                (student_id, student_name)
            )
            connection.commit()

        except sqlite3.IntegrityError:
            connection.close()
            return "Student ID already exists!"

        connection.close()
        return redirect("/register")

    return render_template("register.html")


# ==========================================
# SAVE FACE IMAGE
# ==========================================

@app.route("/save_face", methods=["POST"])
def save_face():
    data = request.get_json()

    student_id = data["student_id"]
    image_data = data["image"]

    image_data = re.sub(
        "^data:image/.+;base64,",
        "",
        image_data
    )

    student_folder = os.path.join(
        "dataset",
        student_id
    )

    os.makedirs(
        student_folder,
        exist_ok=True
    )

    existing_files = os.listdir(student_folder)
    image_number = len(existing_files) + 1

    image_path = os.path.join(
        student_folder,
        f"face_{image_number}.jpg"
    )

    with open(image_path, "wb") as image_file:
        image_file.write(
            base64.b64decode(image_data)
        )

    return jsonify({
        "success": True,
        "message": "Face saved successfully!"
    })


# ==========================================
# TRAIN FACE MODEL
# ==========================================

@app.route("/train_model", methods=["POST"])
def train_model():
    try:
        print()
        print("====================================")
        print("   TRAINING FACE RECOGNITION MODEL")
        print("====================================")

        result = subprocess.run(
            [sys.executable, "encode_faces.py"],
            capture_output=True,
            text=True
        )

        print(result.stdout)

        if result.stderr:
            print("ERROR:")
            print(result.stderr)

        print("====================================")

        if result.returncode == 0:
            print("MODEL TRAINING COMPLETED")
            print("====================================")
            print()

            return jsonify({
                "success": True,
                "message": "Face model trained successfully!"
            })

        else:
            print("MODEL TRAINING FAILED")
            print("====================================")
            print()

            return jsonify({
                "success": False,
                "message": "Model training failed."
            })

    except Exception as error:
        print("Training error:")
        print(error)

        return jsonify({
            "success": False,
            "message": "Model training failed."
        })


# ==========================================
# ATTENDANCE RECORDS
# ==========================================

@app.route("/attendance")
def attendance():
    connection = sqlite3.connect("attendance.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            date,
            time,
            status
        FROM attendance
        ORDER BY date DESC, time DESC
    """)

    records = cursor.fetchall()
    connection.close()

    return render_template(
        "attendance.html",
        records=records
    )


# ==========================================
# EXPORT ATTENDANCE TO CSV
# ==========================================

@app.route("/export_attendance")
def export_attendance():
    connection = sqlite3.connect("attendance.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            attendance.student_id,
            students.name,
            attendance.date,
            attendance.time,
            attendance.status
        FROM attendance
        LEFT JOIN students
        ON attendance.student_id = students.student_id
        ORDER BY attendance.date DESC, attendance.time DESC
    """)

    records = cursor.fetchall()
    connection.close()

    output = io.StringIO()
    writer = csv.writer(output)

    # CSV headings
    writer.writerow([
        "Student ID",
        "Student Name",
        "Date",
        "Time",
        "Status"
    ])

    # Attendance data
    for record in records:
        writer.writerow(record)

    # Excel-friendly UTF-8 encoding
    csv_data = "\ufeff" + output.getvalue()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=attendance_report.csv"
        }
    )


# ==========================================
# TAKE ATTENDANCE
# ==========================================

@app.route("/take_attendance")
def take_attendance():
    try:
        subprocess.Popen(
            [
                sys.executable,
                "recognize_face.py"
            ]
        )

        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Take Attendance</title>
        </head>
        <body>
            <div style="
                text-align:center;
                margin-top:100px;
                font-family:Arial;
            ">
                <h2>
                    Camera started successfully!
                </h2>

                <p>
                    Look at the camera to mark attendance.
                </p>

                <p>
                    Press <b>Q</b>
                    in the camera window to stop.
                </p>

                <br>

                <a href="/">
                    <button>
                        Back to Dashboard
                    </button>
                </a>
            </div>
        </body>
        </html>
        """

    except Exception as error:
        return f"""
        <h2>
            Could not start attendance system.
        </h2>

        <p>{error}</p>

        <br>

        <a href="/">
            <button>
                Back to Dashboard
            </button>
        </a>
        """


# ==========================================
# STUDENT MANAGEMENT
# ==========================================

@app.route("/students")
def students():
    connection = sqlite3.connect("attendance.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            students.student_id,
            students.name,
            COUNT(attendance.id)
        FROM students
        LEFT JOIN attendance
        ON students.student_id = attendance.student_id
        GROUP BY
            students.student_id,
            students.name
        ORDER BY
            students.student_id
    """)

    students_list = cursor.fetchall()
    connection.close()

    return render_template(
        "students.html",
        students=students_list
    )


# ==========================================
# INDIVIDUAL STUDENT ATTENDANCE
# ==========================================

@app.route("/student/<student_id>")
def student_attendance(student_id):
    connection = sqlite3.connect("attendance.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            name
        FROM students
        WHERE student_id = ?
    """, (student_id,))

    student = cursor.fetchone()

    if student is None:
        connection.close()
        return "Student not found!"

    cursor.execute("""
        SELECT
            date,
            time,
            status
        FROM attendance
        WHERE student_id = ?
        ORDER BY
            date DESC,
            time DESC
    """, (student_id,))

    attendance_records = cursor.fetchall()
    connection.close()

    return render_template(
        "student_attendance.html",
        student=student,
        attendance_records=attendance_records
    )


# ==========================================
# ATTENDANCE ANALYTICS
# ==========================================

@app.route("/analytics")
def analytics():
    connection = sqlite3.connect("attendance.db")
    cursor = connection.cursor()

    # Total students
    cursor.execute("""
        SELECT COUNT(*)
        FROM students
    """)
    total_students = cursor.fetchone()[0]

    # Total recorded attendance days
    cursor.execute("""
        SELECT COUNT(DISTINCT date)
        FROM attendance
    """)
    total_days = cursor.fetchone()[0]

    # Total attendance records
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
    """)
    total_records = cursor.fetchone()[0]

    # Student-wise analytics
    cursor.execute("""
        SELECT
            students.student_id,
            students.name,
            COUNT(DISTINCT attendance.date)
        FROM students
        LEFT JOIN attendance
        ON students.student_id = attendance.student_id
        GROUP BY
            students.student_id,
            students.name
        ORDER BY
            students.student_id
    """)

    student_data = cursor.fetchall()
    analytics_data = []

    for student_id, name, days_present in student_data:
        if total_days > 0:
            attendance_rate = (
                days_present / total_days
            ) * 100
        else:
            attendance_rate = 0

        analytics_data.append({
            "student_id": student_id,
            "name": name,
            "days_present": days_present,
            "total_days": total_days,
            "attendance_rate": round(
                attendance_rate,
                1
            )
        })

    connection.close()

    return render_template(
        "analytics.html",
        total_students=total_students,
        total_days=total_days,
        total_records=total_records,
        analytics_data=analytics_data
    )


# ==========================================
# RUN FLASK
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)
