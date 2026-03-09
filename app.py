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

    today = str(datetime.now().date())
    time_now = datetime.now().strftime("%H:%M")

    # Get all records from the sheet
    records = sheet.get_all_records()

    # Check if the student has already marked attendance for this lecture today
    for r in records:
        if (
            str(r["Roll"]) == str(roll)
            and r["Date"] == today
            and str(r["Lecture"]) == str(SESSION["lecture"])
        ):
            return jsonify({"status": "already_marked"})

    # Ensure the headers in the sheet match this order:
    # Date | Time | Name | Roll | Division | Subject | Lecture | Teacher
    row = [
        today,
        time_now,
        name,
        roll,
        division,
        SESSION["subject"],
        SESSION["lecture"],
        SESSION["teacher"],
    ]

    # Append the row to the sheet
    sheet.append_row(row, value_input_option="USER_ENTERED")

    return jsonify({"status": "present"})
