import numpy as np
import cv2
import dlib
import urllib.request
import bz2
import os
import time
import math
from scipy.spatial import distance as dist


def download_model():
    model_file = "shape_predictor_68_face_landmarks.dat"
    model_bz2 = model_file + ".bz2"

    if not os.path.exists(model_file):
        print("Dang tai xuong mo hinh phat hien dac diem khuon mat...")
        url = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
        urllib.request.urlretrieve(url, model_bz2)

        print("Dang giai nen mo hinh...")
        with open(model_file, 'wb') as new_file, bz2.BZ2File(model_bz2, 'rb') as file:
            for data in iter(lambda: file.read(100 * 1024), b''):
                new_file.write(data)

        os.remove(model_bz2)
        print("Mo hinh da san sang.")

    return model_file


def calculate_ear(eye_points):
    # Tinh khoang cach theo chieu doc
    A = dist.euclidean(eye_points[1], eye_points[5])
    B = dist.euclidean(eye_points[2], eye_points[4])

    # Tinh khoang cach theo chieu ngang
    C = dist.euclidean(eye_points[0], eye_points[3])

    # Tinh EAR
    ear = (A + B) / (2.0 * C)
    return ear


def calculate_mar(mouth_points):
    # Tinh ti le mieng mo
    A = dist.euclidean(mouth_points[13], mouth_points[19])
    B = dist.euclidean(mouth_points[14], mouth_points[18])
    C = dist.euclidean(mouth_points[15], mouth_points[17])
    D = dist.euclidean(mouth_points[12], mouth_points[16])

    mar = (A + B + C) / (3.0 * D)
    return mar


def eye_aspect_ratio_variance(ear_history, window_size=30):
    """Tinh do dao dong cua EAR de nhan dien met moi"""
    if len(ear_history) < window_size:
        return 0
    return np.var(ear_history[-window_size:])


# Cac thong so cau hinh
EAR_THRESHOLD = 0.2  # Nguong EAR cho mat nham
MAR_THRESHOLD = 0.5  # Nguong MAR cho mieng mo
EAR_CONSEC_FRAMES = 40  # So frame lien tiep cho ngu gat
BLINK_CONSEC_FRAMES = 3  # So frame toi da cho mot lan chop mat binh thuong
EAR_VARIANCE_THRESHOLD = 0.001  # Nguong do dao dong EAR cho met moi
BLINK_FREQUENCY_THRESHOLD = 0.5  # Nguong tan so chop mat (lan/giay) cho met moi
NO_FACE_ALERT_FRAMES = 60  # So frame khong co khuon mat de canh bao
EYE_FATIGUE_THRESHOLD = 20  # Nguong so khung hinh de canh bao mat moi

# Cac mau sac
PRIMARY_COLOR = (0, 255, 0)  # Xanh la
SECONDARY_COLOR = (0, 255, 255)  # Vang
ALERT_COLOR = (0, 0, 255)  # Do
TEXT_COLOR = (255, 255, 255)  # Trang
FACE_MESH_COLOR = (0, 255, 0)  # Xanh la

# Khoi tao cac bien dem va theo doi
frame_count = 0  # Dem frame cho ngu gat
no_face_count = 0  # Dem frame khong co khuon mat
yawn_count = 0  # Dem frame ngap
blink_counter = 0  # Dem frame chop mat hien tai
blink_total = 0  # Tong so lan chop mat
last_blink_time = time.time()
blink_start_time = time.time()
ear_history = []  # Luu tru lich su EAR
mode = "default"  # Che do hien tai: default, drowsy, sleeping, distracted, tired
calibration_ears = []  # Dung de hieu chinh EAR cho tung nguoi
calibration_complete = False
alert_start_time = None

# Bien dem cho tinh nang mat moi
eye_fatigue_frames = 0  # Dem frame cho mat moi
eye_fatigue_alert_active = False  # Co bao hieu trang thai canh bao mat moi
eye_fatigue_alert_start_time = 0  # Thoi diem bat dau canh bao mat moi

# Khoi tao detector va predictor
print("Khoi tao he thong nhan dien...")
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(download_model())

# Dinh nghia cac vung landmark
FACIAL_LANDMARKS_INDEXES = {
    "right_eye": (36, 42),
    "left_eye": (42, 48),
    "jaw": (0, 17),
    "nose": (27, 36),
    "mouth": (48, 68)
}

# Khoi tao camera
print("Khoi tao camera...")
cap = cv2.VideoCapture(1)  # Thu camera 0 truoc
if not cap.isOpened():
    print("Khong the mo camera 0, thu camera 1...")
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Khong the mo camera!")
        exit()

# FPS counter va thoi gian bat dau
fps = 0
start_time = time.time()
frame_counter = 0
session_start_time = time.time()

print("He thong da san sang. Nhan 'q' de thoat.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Loi khi doc frame tu camera!")
        break

    # Tinh FPS
    frame_counter += 1
    current_time = time.time()
    if current_time - start_time >= 1.0:
        fps = frame_counter / (current_time - start_time)
        frame_counter = 0
        start_time = current_time

    # Xu ly frame
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    overlay = frame.copy()
    output = frame.copy()

    # Phat hien khuon mat
    faces = detector(gray, 0)

    # Kiem tra neu khong co khuon mat nao duoc phat hien
    if len(faces) == 0:
        no_face_count += 1
        if no_face_count > NO_FACE_ALERT_FRAMES:
            mode = "distracted"
            # Tao hieu ung canh bao
            warning_overlay = overlay.copy()
            cv2.rectangle(warning_overlay, (0, 0), (frame.shape[1], frame.shape[0]), SECONDARY_COLOR, -1)
            cv2.addWeighted(warning_overlay, 0.3, output, 0.7, 0, output)

            # Hien thi canh bao
            alert_text = "KHONG PHAT HIEN NGUOI LAI XE!"
            text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
            text_x = (frame.shape[1] - text_size[0]) // 2
            cv2.putText(output, alert_text, (text_x, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, ALERT_COLOR, 2)
    else:
        no_face_count = 0
        # Chon khuon mat lon nhat de xu ly
        face = max(faces, key=lambda rect: (rect.right() - rect.left()) * (rect.bottom() - rect.top()))

        # Phat hien landmarks
        shape = predictor(gray, face)
        shape = np.array([[p.x, p.y] for p in shape.parts()])

        # Ve khung mat va landmark
        x1, y1 = face.left(), face.top()
        x2, y2 = face.right(), face.bottom()
        cv2.rectangle(output, (x1, y1), (x2, y2), PRIMARY_COLOR, 2)

        # Ve cac diem landmark va ket noi
        for region, (start_idx, end_idx) in FACIAL_LANDMARKS_INDEXES.items():
            pts = shape[start_idx:end_idx]
            if len(pts) > 1:
                cv2.polylines(output, [pts], True, FACE_MESH_COLOR, 1)

        # Tinh toan cac chi so
        left_eye = shape[42:48]
        right_eye = shape[36:42]
        mouth_points = shape[48:68]

        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)
        ear = (left_ear + right_ear) / 2.0
        ear_history.append(ear)

        mar = calculate_mar(mouth_points)

        # Giai doan hieu chuan
        if not calibration_complete and len(calibration_ears) < 100:
            calibration_ears.append(ear)
            cv2.putText(output, f"Hieu chuan: {len(calibration_ears)}%", (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_COLOR, 2)

            if len(calibration_ears) == 100:
                # Tinh toan nguong EAR ca nhan hoa
                avg_ear = np.mean(calibration_ears)
                EAR_THRESHOLD = avg_ear * 0.8  # 80% cua EAR trung binh khi mat mo
                calibration_complete = True
                print(f"Hieu chuan hoan tat: EAR_THRESHOLD = {EAR_THRESHOLD:.3f}")

        else:  # Sau khi hieu chuan
            # Logic phat hien ngu gat va cac tinh huong khac

            # 1. Phat hien chop mat va ngu gat
            if ear < EAR_THRESHOLD:
                frame_count += 1
                blink_counter += 1
                eye_fatigue_frames += 1

                # Kiem tra mat moi (them moi)
                if eye_fatigue_frames >= EYE_FATIGUE_THRESHOLD and not eye_fatigue_alert_active:
                    eye_fatigue_alert_active = True
                    eye_fatigue_alert_start_time = time.time()

                # Kiem tra ngu guc
                if frame_count >= EAR_CONSEC_FRAMES:
                    mode = "sleeping"
                    if alert_start_time is None:
                        alert_start_time = time.time()

                    # Tao hieu ung canh bao manh cho ngu guc
                    alpha = 0.4 + 0.2 * np.sin(time.time() * 8)  # Hieu ung nhap nhay
                    warning_overlay = overlay.copy()
                    cv2.rectangle(warning_overlay, (0, 0), (frame.shape[1], frame.shape[0]), ALERT_COLOR, -1)
                    cv2.addWeighted(warning_overlay, alpha, output, 1 - alpha, 0, output)

                    # Hien thi canh bao lon
                    alert_text = "CANH BAO NGU GUC!"
                    text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
                    text_x = (frame.shape[1] - text_size[0]) // 2
                    text_y = (frame.shape[0] + text_size[1]) // 2
                    cv2.putText(output, alert_text, (text_x, text_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, ALERT_COLOR, 3)

                    alert_duration = int(current_time - alert_start_time)
                    cv2.putText(output, f"Thoi gian ngu: {alert_duration}s", (20, 150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, ALERT_COLOR, 2)
            else:
                # Reset canh bao ngu gat
                if frame_count >= EAR_CONSEC_FRAMES:
                    alert_start_time = None

                # Kiem tra hoan thanh mot lan chop mat
                if blink_counter >= BLINK_CONSEC_FRAMES:
                    if current_time - last_blink_time > 0.5:  # Dam bao khong dem lien tuc
                        blink_total += 1
                        last_blink_time = current_time

                # Reset cac bien dem
                frame_count = 0
                blink_counter = 0
                eye_fatigue_frames = 0
                mode = "default"

            # Hien thi canh bao mat moi (them moi)
            if eye_fatigue_alert_active and mode != "sleeping":  # Khong hien thi khi dang co canh bao ngu gat
                # Tao lop phu canh bao
                warning_overlay = overlay.copy()

                # Tao van ban canh bao
                alert_text = "CANH BAO: MAT MOI!"

                # Tinh toan vi tri va kich thuoc van ban
                text_size = 1.0
                text_thickness = 2
                (text_width, text_height), _ = cv2.getTextSize(
                    alert_text, cv2.FONT_HERSHEY_SIMPLEX, text_size, text_thickness
                )
                text_x = (warning_overlay.shape[1] - text_width) // 2
                text_y = (warning_overlay.shape[0] + text_height) // 2

                # Hien thi van ban canh bao voi mau do
                cv2.putText(
                    warning_overlay,
                    alert_text,
                    (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    text_size,
                    ALERT_COLOR,  # Mau do
                    text_thickness
                )

                # Them hieu ung nhap nhay (thay doi do trong suot)
                elapsed_time = time.time() - eye_fatigue_alert_start_time
                alpha = 0.4 + 0.3 * abs(math.sin(elapsed_time * 5))  # Tao hieu ung nhap nhay

                # Ket hop lop phu canh bao voi frame chinh
                cv2.addWeighted(warning_overlay, alpha, output, 1 - alpha, 0, output)

                # Tu dong tat canh bao sau mot khoang thoi gian (vi du: 5 giay) hoac khi mat mo lai
                if time.time() - eye_fatigue_alert_start_time > 5.0 and ear > EAR_THRESHOLD:
                    eye_fatigue_alert_active = False

            # 2. Phat hien ngap
            if mar > MAR_THRESHOLD:
                yawn_count += 1
                if yawn_count >= 20:
                    if mode != "sleeping" and not eye_fatigue_alert_active:  # Uu tien canh bao ngu gat va mat moi
                        mode = "drowsy"

                        # Tao hieu ung canh bao cho ngap
                        warning_overlay = overlay.copy()
                        cv2.rectangle(warning_overlay, (0, 0), (frame.shape[1], frame.shape[0]), SECONDARY_COLOR, -1)
                        cv2.addWeighted(warning_overlay, 0.3, output, 0.7, 0, output)

                        # Hien thi canh bao
                        cv2.putText(output, "PHAT HIEN NGAP - CO DAU HIEU MET MOI!", (20, 100),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, SECONDARY_COLOR, 2)
            else:
                yawn_count = max(0, yawn_count - 1)

            # 3. Phat hien met moi dua vao tan so chop mat
            session_time = current_time - session_start_time
            if session_time > 30:  # Sau 30 giay theo doi
                blink_frequency = blink_total / session_time  # Tan so chop mat (lan/giay)

                # Tinh do dao dong cua EAR
                ear_var = eye_aspect_ratio_variance(ear_history)

                # Phat hien met moi qua tan so chop mat cao hoac dao dong EAR thap
                if (blink_frequency > BLINK_FREQUENCY_THRESHOLD or
                        (ear_var < EAR_VARIANCE_THRESHOLD and len(ear_history) > 100)):
                    if mode == "default" and not eye_fatigue_alert_active:  # Khong ghi de len cac canh bao nghiem trong hon
                        mode = "tired"

                        # Hien thi dau hieu met moi
                        cv2.putText(output, "DAU HIEU MET MOI - NGHI NGOI!", (20, 120),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, SECONDARY_COLOR, 2)

            # Ve thanh trang thai EAR
            bar_length = 150
            filled_length = int(bar_length * (ear / 0.4))  # 0.4 la gia tri EAR toi da
            filled_length = min(filled_length, bar_length)

            bar_height = 20
            bar_x = 20
            bar_y = 50

            # Xac dinh mau cho thanh EAR
            if ear < EAR_THRESHOLD:
                bar_color = ALERT_COLOR
            else:
                bar_color = PRIMARY_COLOR

            cv2.rectangle(output, (bar_x, bar_y), (bar_x + bar_length, bar_y + bar_height), (50, 50, 50), -1)
            cv2.rectangle(output, (bar_x, bar_y), (bar_x + filled_length, bar_y + bar_height), bar_color, -1)

            # Hien thi chi so va trang thai
            status_text = f"Trang thai: {mode.upper()}"
            if eye_fatigue_alert_active:
                status_text += " (MAT MOI)"

            metrics = [
                f"EAR: {ear:.3f} (Nguong: {EAR_THRESHOLD:.3f})",
                f"MAR: {mar:.3f}",
                f"Chop mat: {blink_total} (Tan so: {blink_total / max(1, current_time - session_start_time):.2f}/giay)",
                f"FPS: {fps:.1f}"
            ]

            cv2.putText(output, status_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXT_COLOR, 1)

            for i, metric in enumerate(metrics):
                cv2.putText(output, metric, (20, 80 + i * 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXT_COLOR, 1)

    # Hien thi frame
    cv2.imshow("He thong Phat hien Ngu gat", output)

    # Thoat khi nhan q
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giai phong tai nguyen
cap.release()
cv2.destroyAllWindows()
print("Da thoat chuong trinh.")