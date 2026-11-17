import cv2
import sqlite3
from datetime import datetime
import time


# ==========================================
# DATABASE
# ==========================================

def get_student_name(student_id):

    connection = sqlite3.connect("attendance.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT name
        FROM students
        WHERE student_id = ?
        """,
        (str(student_id),)
    )

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return "Student Not Found"


def mark_attendance(student_id):

    connection = sqlite3.connect("attendance.db")
    cursor = connection.cursor()

    now = datetime.now()

    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    # Check if already marked today
    cursor.execute(
        """
        SELECT id
        FROM attendance
        WHERE student_id = ?
        AND date = ?
        """,
        (str(student_id), current_date)
    )

    existing_record = cursor.fetchone()

    if existing_record:

        connection.close()

        return False

    cursor.execute(
        """
        INSERT INTO attendance
        (student_id, date, time, status)
        VALUES (?, ?, ?, ?)
        """,
        (
            str(student_id),
            current_date,
            current_time,
            "Present"
        )
    )

    connection.commit()

    connection.close()

    return True


# ==========================================
# LOAD FACE MODEL
# ==========================================

recognizer = cv2.face.LBPHFaceRecognizer_create()

recognizer.read(
    "encodings/face_model.yml"
)


# ==========================================
# FACE DETECTOR
# ==========================================

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades
    + "haarcascade_frontalface_default.xml"
)


# ==========================================
# OPEN CAMERA
# ==========================================

print("Starting camera...")

camera = cv2.VideoCapture(
    0,
    cv2.CAP_DSHOW
)


# Set camera resolution
camera.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    640
)

camera.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    480
)


if not camera.isOpened():

    print("ERROR: Camera could not be opened.")

    exit()


print("Camera opened successfully.")
print("Press Q to exit.")


# ==========================================
# ATTENDANCE CONTROL
# ==========================================

last_student_id = None

last_attendance_check = 0

attendance_message = ""

attendance_message_time = 0


# ==========================================
# MAIN LOOP
# ==========================================

while True:

    success, frame = camera.read()


    if not success:

        print("ERROR: Could not read camera frame.")

        break


    # ==========================================
    # FLIP CAMERA
    # ==========================================

    frame = cv2.flip(
        frame,
        1
    )


    # ==========================================
    # GRAYSCALE
    # ==========================================

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )


    # ==========================================
    # DETECT FACES
    # ==========================================

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(100, 100)
    )


    # ==========================================
    # PROCESS EACH FACE
    # ==========================================

    for (x, y, w, h) in faces:

        face = gray[
            y:y + h,
            x:x + w
        ]


        # ==========================================
        # RECOGNIZE FACE
        # ==========================================

        student_id, confidence = recognizer.predict(
            face
        )


        # Lower LBPH confidence = better match
        if confidence < 100:

            student_name = get_student_name(
                student_id
            )


            current_time = time.time()


            # Prevent repeated database checks
            if (
                student_id != last_student_id
                or
                current_time - last_attendance_check > 10
            ):

                attendance_marked = mark_attendance(
                    student_id
                )


                last_student_id = student_id

                last_attendance_check = current_time


                if attendance_marked:

                    attendance_message = (
                        "Attendance Marked!"
                    )

                else:

                    attendance_message = (
                        "Already Marked Today"
                    )


                attendance_message_time = (
                    current_time
                )


            # ==========================================
            # GREEN FACE BOX
            # ==========================================

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )


            # Student name

            cv2.putText(
                frame,
                student_name,
                (x, y - 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )


            # Student ID

            cv2.putText(
                frame,
                f"ID: {student_id}",
                (x, y - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2
            )


            # Confidence

            cv2.putText(
                frame,
                f"Score: {confidence:.1f}",
                (x, y + h + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )


        else:

            # ==========================================
            # UNKNOWN FACE
            # ==========================================

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 0, 255),
                2
            )


            cv2.putText(
                frame,
                "Unknown",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )


    # ==========================================
    # ATTENDANCE MESSAGE
    # ==========================================

    if (
        time.time() - attendance_message_time
        < 5
        and attendance_message != ""
    ):

        cv2.putText(
            frame,
            attendance_message,
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )


    # ==========================================
    # DISPLAY CAMERA
    # ==========================================

    cv2.imshow(
        "Smart Attendance System",
        frame
    )


    # ==========================================
    # EXIT WITH Q
    # ==========================================

    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


# ==========================================
# CLOSE CAMERA
# ==========================================

camera.release()

cv2.destroyAllWindows()

print("Camera closed.")
print("Smart Attendance System stopped.")