from flask_cors import CORS
from flask import Flask, request, jsonify, send_file
import pandas as pd
import qrcode
from datetime import datetime
from io import BytesIO
import os

app = Flask(__name__)

# Replace "*" with your frontend URL after deployment for security
CORS(app, resources={r"/*": {"origins": "*"}})

students_file = "data/students.xlsx"     # moved to 'data' folder
teachers_file = "data/teachers.xlsx"
attendance_file = "data/attendance.xlsx"

SESSION = {}

# -------------------------
# TEACHER LOGIN
# -------------------------
@app.route("/teacher_login", methods=["POST"])
def teacher_login():
    data = request.json
    username = str(data.get("username"))
    password = str(data.get("password"))

    df = pd.read_excel(teachers_file)
    df["username"] = df["username"].astype(str)
    df["password"] = df["password"].astype(str)

    user = df[(df["username"] == username) & (df["password"] == password)]
    if not user.empty:
        SESSION["teacher"] = username
        return jsonify({"status": "success"})

    return jsonify({"status": "invalid"})


# -------------------------
# START SESSION
# -------------------------
@app.route("/start_session", methods=["POST"])
def start_session():
    data = request.json
    division = data["division"]
    lecture = int(data["lecture"])
    teacher = data["teacher"]

    timetable_file = f"data/timetable{division}.xlsx"
    if os.path.exists(timetable_file):
        timetable = pd.read_excel(timetable_file)
    else:
        return jsonify({"status": "timetable_missing"})

    today = datetime.now().strftime("%A")
    lec = timetable[(timetable["Day"] == today) & (timetable["Lecture"] == lecture)]

    if lec.empty:
        return jsonify({"status": "no_lecture_today"})

    subject = lec.iloc[0]["Subject"]
    session_id = str(datetime.now().timestamp())

    SESSION["session"] = session_id
    SESSION["division"] = division
    SESSION["lecture"] = lecture
    SESSION["subject"] = subject
    SESSION["teacher"] = teacher

    return jsonify({
        "status": "session_started",
        "subject": subject,
        "session": session_id
    })


# -------------------------
# STOP SESSION
# -------------------------
@app.route("/stop_session", methods=["POST"])
def stop_session():
    SESSION.clear()
    return jsonify({"status": "stopped"})


# -------------------------
# STUDENT LOGIN
# -------------------------
@app.route("/student_login", methods=["POST"])
def student_login():
    data = request.json
    username = str(data.get("username")).strip()
    password = str(data.get("password")).strip()

    df = pd.read_excel(students_file, dtype=str)
    df["Username"] = df["Username"].str.strip()
    df["Password"] = df["Password"].str.strip()

    user = df[(df["Username"] == username) & (df["Password"] == password)]
    if user.empty:
        return jsonify({"status": "fail"})

    student = user.iloc[0]
    return jsonify({
        "status": "success",
        "name": student["Name"],
        "roll": str(student["Roll"]),
        "division": student["Division"]
    })


# -------------------------
# GENERATE QR
# -------------------------
@app.route("/generate_qr")
def generate_qr():
    session_id = SESSION.get("session")
    if not session_id:
        return jsonify({"error": "session not started"})

    # Replace with your deployed frontend URL
    frontend_url = "https://YOUR_FRONTEND_URL"  
    url = f"{frontend_url}/verify.html?session={session_id}"

    img = qrcode.make(url)
    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")


# -------------------------
# MARK ATTENDANCE
# -------------------------
@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    if "session" not in SESSION:
        return jsonify({"status": "attendance_closed"})

    data = request.json
    name = data.get("name")
    roll = data.get("roll")
    division = data.get("division")

    if not all([name, roll, division]):
        return jsonify({"status": "error", "message": "Incomplete data"})

    if division != SESSION["division"]:
        return jsonify({"status": "wrong_division"})

    if os.path.exists(attendance_file):
        df = pd.read_excel(attendance_file)
    else:
        df = pd.DataFrame(columns=[
            "Date", "Time", "Name", "Roll", "Division",
            "Subject", "Lecture", "Teacher"
        ])

    today = str(datetime.now().date())
    existing = df[
        (df["Roll"].astype(str) == str(roll)) &
        (df["Date"] == today) &
        (df["Lecture"] == SESSION["lecture"])
    ]

    if not existing.empty:
        return jsonify({"status": "already_marked"})

    row = {
        "Date": today,
        "Time": datetime.now().strftime("%H:%M"),
        "Name": name,
        "Roll": roll,
        "Division": division,
        "Subject": SESSION["subject"],
        "Lecture": SESSION["lecture"],
        "Teacher": SESSION["teacher"]
    }

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    try:
        df.to_excel(attendance_file, index=False)
    except PermissionError:
        return jsonify({"status": "file_open_error"})

    return jsonify({"status": "present"})


# -------------------------
# VIEW ATTENDANCE BY DIVISION
# -------------------------
@app.route("/attendance_by_division")
def attendance_by_division():
    division = request.args.get("division")
    if not os.path.exists(attendance_file):
        return jsonify([])

    df = pd.read_excel(attendance_file)
    df = df[df["Division"] == division]
    return jsonify(df.to_dict(orient="records"))


# -------------------------
# RUN SERVER
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)