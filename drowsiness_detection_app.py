import numpy as np
import cv2
import dlib
import urllib.request
import bz2
import os
import time
import math
from scipy.spatial import distance as dist
from concurrent.futures import ThreadPoolExecutor
import threading
import pickle
from collections import deque


class Config:
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

    # Duong dan va tep
    MODEL_FILE = "shape_predictor_68_face_landmarks.dat"
    MODEL_URL = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
    CALIB_FILE = "calibration.pkl"

    # Vung landmark
    FACIAL_LANDMARKS_INDEXES = {
        "right_eye": (36, 42),
        "left_eye": (42, 48),
        "jaw": (0, 17),
        "nose": (27, 36),
        "mouth": (48, 68)
    }

    def save_calibration(self, ear_threshold):
        """Luu nguong EAR da hieu chinh"""
        with open(self.CALIB_FILE, 'wb') as f:
            pickle.dump({'ear_threshold': ear_threshold}, f)

    def load_calibration(self):
        """Tai nguong EAR da hieu chinh"""
        if os.path.exists(self.CALIB_FILE):
            with open(self.CALIB_FILE, 'rb') as f:
                data = pickle.load(f)
                self.EAR_THRESHOLD = data.get('ear_threshold', self.EAR_THRESHOLD)
                return True
        return False


class ModelManager:
    """Quan ly viec tai xuong va tai mo hinh"""

    def __init__(self, config):
        self.config = config
        self._detector = None
        self._predictor = None

    def download_model(self):
        model_file = self.config.MODEL_FILE
        model_bz2 = model_file + ".bz2"

        if not os.path.exists(model_file):
            print("Dang tai xuong mo hinh phat hien dac diem khuon mat...")
            urllib.request.urlretrieve(self.config.MODEL_URL, model_bz2)

            print("Dang giai nen mo hinh...")
            with open(model_file, 'wb') as new_file, bz2.BZ2File(model_bz2, 'rb') as file:
                for data in iter(lambda: file.read(100 * 1024), b''):
                    new_file.write(data)

            os.remove(model_bz2)
            print("Mo hinh da san sang.")

        return model_file

    @property
    def detector(self):
        if self._detector is None:
            self._detector = dlib.get_frontal_face_detector()
        return self._detector

    @property
    def predictor(self):
        if self._predictor is None:
            self._predictor = dlib.shape_predictor(self.download_model())
        return self._predictor


class FacialAnalyzer:
    """Phan tich cac chi so khuon mat"""

    def __init__(self, config):
        self.config = config

    def calculate_ear(self, eye_points):
        """Tinh he so EAR"""
        # Vector hoa tinh toan de tang hieu suat
        vertical_dist = [
            dist.euclidean(eye_points[1], eye_points[5]),
            dist.euclidean(eye_points[2], eye_points[4])
        ]
        horizontal_dist = dist.euclidean(eye_points[0], eye_points[3])

        return sum(vertical_dist) / (2.0 * horizontal_dist) if horizontal_dist > 0 else 0

    def calculate_mar(self, mouth_points):
        """Tinh ti le mieng mo"""
        A = dist.euclidean(mouth_points[13], mouth_points[19])
        B = dist.euclidean(mouth_points[14], mouth_points[18])
        C = dist.euclidean(mouth_points[15], mouth_points[17])
        D = dist.euclidean(mouth_points[12], mouth_points[16])

        return (A + B + C) / (3.0 * D) if D > 0 else 0

    def eye_aspect_ratio_variance(self, ear_history, window_size=30):
        """Tinh do dao dong cua EAR de nhan dien met moi"""
        if len(ear_history) < window_size:
            return 0
        return np.var(ear_history[-window_size:])


class AlertSystem:
    """He thong quan ly canh bao va hien thi"""

    def __init__(self, config):
        self.config = config
        self.mode = "default"  # Che do hien tai: default, drowsy, sleeping, distracted, tired
        self.alert_start_time = None
        self.eye_fatigue_alert_active = False
        self.eye_fatigue_alert_start_time = 0

    def render_drowsiness_alert(self, frame, duration=None):
        """Hien thi canh bao ngu gat"""
        overlay = frame.copy()
        alpha = 0.4 + 0.2 * np.sin(time.time() * 8)  # Hieu ung nhap nhay
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), self.config.ALERT_COLOR, -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        # Hien thi canh bao lon
        alert_text = "CANH BAO NGU GUC!"
        text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = (frame.shape[0] + text_size[1]) // 2
        cv2.putText(frame, alert_text, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, self.config.ALERT_COLOR, 3)

        if duration is not None:
            cv2.putText(frame, f"Thoi gian ngu: {duration}s", (20, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.config.ALERT_COLOR, 2)

        return frame

    def render_distraction_alert(self, frame):
        """Hien thi canh bao mat tap trung"""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), self.config.SECONDARY_COLOR, -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

        # Hien thi canh bao
        alert_text = "KHONG PHAT HIEN NGUOI LAI XE!"
        text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        cv2.putText(frame, alert_text, (text_x, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, self.config.ALERT_COLOR, 2)

        return frame

    def render_fatigue_alert(self, frame):
        """Hien thi canh bao mat moi"""
        overlay = frame.copy()
        elapsed_time = time.time() - self.eye_fatigue_alert_start_time
        alpha = 0.4 + 0.3 * abs(math.sin(elapsed_time * 5))  # Tao hieu ung nhap nhay

        # Tao van ban canh bao
        alert_text = "CANH BAO: MAT MOI!"

        # Tinh toan vi tri va kich thuoc van ban
        text_size = 1.0
        text_thickness = 2
        (text_width, text_height), _ = cv2.getTextSize(
            alert_text, cv2.FONT_HERSHEY_SIMPLEX, text_size, text_thickness
        )
        text_x = (overlay.shape[1] - text_width) // 2
        text_y = (overlay.shape[0] + text_height) // 2

        # Hien thi van ban canh bao voi mau do
        cv2.putText(
            overlay,
            alert_text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            text_size,
            self.config.ALERT_COLOR,
            text_thickness
        )

        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        return frame

    def render_yawn_alert(self, frame):
        """Hien thi canh bao ngap"""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), self.config.SECONDARY_COLOR, -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

        cv2.putText(frame, "PHAT HIEN NGAP - CO DAU HIEU MET MOI!", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.config.SECONDARY_COLOR, 2)
        return frame

    def render_status_bar(self, frame, ear, ear_threshold):
        """Hien thi thanh trang thai EAR"""
        bar_length = 150
        filled_length = int(bar_length * (ear / 0.4))  # 0.4 la gia tri EAR toi da
        filled_length = min(filled_length, bar_length)

        bar_height = 20
        bar_x = 20
        bar_y = 50

        # Xac dinh mau cho thanh EAR
        bar_color = self.config.ALERT_COLOR if ear < ear_threshold else self.config.PRIMARY_COLOR

        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_length, bar_y + bar_height), (50, 50, 50), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled_length, bar_y + bar_height), bar_color, -1)

        return frame

    def render_metrics(self, frame, metrics, status_text):
        """Hien thi cac chi so va trang thai"""
        cv2.putText(frame, status_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.config.TEXT_COLOR, 1)

        for i, metric in enumerate(metrics):
            cv2.putText(frame, metric, (20, 80 + i * 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.config.TEXT_COLOR, 1)

        return frame


class DrowsinessDetector:
    """He thong phat hien ngu gat chinh"""

    def __init__(self):
        self.config = Config()
        self.model_manager = ModelManager(self.config)
        self.analyzer = FacialAnalyzer(self.config)
        self.alert_system = AlertSystem(self.config)

        # Bien trang thai
        self.frame_count = 0  # Dem frame cho ngu gat
        self.no_face_count = 0  # Dem frame khong co khuon mat
        self.yawn_count = 0  # Dem frame ngap
        self.blink_counter = 0  # Dem frame chop mat hien tai
        self.blink_total = 0  # Tong so lan chop mat
        self.last_blink_time = time.time()
        self.blink_start_time = time.time()
        self.ear_history = deque(maxlen=300)  # Luu tru lich su EAR voi kich thuoc toi da
        self.eye_fatigue_frames = 0  # Dem frame cho mat moi

        # Hieu chinh
        self.calibration_ears = []
        self.calibration_complete = self.config.load_calibration()

        # FPS va thoi gian
        self.fps = 0
        self.start_time = time.time()
        self.frame_counter = 0
        self.session_start_time = time.time()

        # Khoi tao camera
        self.cap = None

    def start_camera(self):
        """Khoi tao camera"""
        print("Khoi tao camera...")
        try:
            self.cap = cv2.VideoCapture(0)  # Thu camera 0 truoc
            if not self.cap.isOpened():
                print("Khong the mo camera 0, thu camera 1...")
                self.cap = cv2.VideoCapture(1)
                if not self.cap.isOpened():
                    raise IOError("Khong the mo camera!")
        except Exception as e:
            print(f"Loi khi khoi tao camera: {e}")
            raise

    def process_face(self, gray, face, frame):
        """Xu ly khuon mat da phat hien"""
        shape = self.model_manager.predictor(gray, face)
        shape_np = np.array([[p.x, p.y] for p in shape.parts()])

        # Ve khung mat va landmark
        x1, y1 = face.left(), face.top()
        x2, y2 = face.right(), face.bottom()
        cv2.rectangle(frame, (x1, y1), (x2, y2), self.config.PRIMARY_COLOR, 2)

        # Ve cac diem landmark va ket noi
        for region, (start_idx, end_idx) in self.config.FACIAL_LANDMARKS_INDEXES.items():
            pts = shape_np[start_idx:end_idx]
            if len(pts) > 1:
                cv2.polylines(frame, [pts], True, self.config.FACE_MESH_COLOR, 1)

        # Tinh toan cac chi so
        left_eye = shape_np[42:48]
        right_eye = shape_np[36:42]
        mouth_points = shape_np[48:68]

        left_ear = self.analyzer.calculate_ear(left_eye)
        right_ear = self.analyzer.calculate_ear(right_eye)
        ear = (left_ear + right_ear) / 2.0
        self.ear_history.append(ear)

        mar = self.analyzer.calculate_mar(mouth_points)

        return ear, mar, shape_np

    def handle_calibration(self, ear, frame):
        """Xu ly hieu chinh"""
        if not self.calibration_complete and len(self.calibration_ears) < 100:
            self.calibration_ears.append(ear)
            cv2.putText(frame, f"Hieu chinh: {len(self.calibration_ears)}%", (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.config.TEXT_COLOR, 2)

            if len(self.calibration_ears) == 100:
                # Tinh toan nguong EAR ca nhan hoa
                avg_ear = np.mean(self.calibration_ears)
                self.config.EAR_THRESHOLD = avg_ear * 0.8  # 80% cua EAR trung binh khi mat mo
                self.config.save_calibration(self.config.EAR_THRESHOLD)
                self.calibration_complete = True
                print(f"Hieu chinh hoan tat: EAR_THRESHOLD = {self.config.EAR_THRESHOLD:.3f}")
            return True
        return False

    def process_frame(self):
        """Xu ly mot frame tu camera"""
        ret, frame = self.cap.read()
        if not ret:
            print("Loi khi doc frame tu camera!")
            return None

        # Tinh FPS
        self.frame_counter += 1
        current_time = time.time()
        if current_time - self.start_time >= 1.0:
            self.fps = self.frame_counter / (current_time - self.start_time)
            self.frame_counter = 0
            self.start_time = current_time

        # Xu ly frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        overlay = frame.copy()
        output = frame.copy()

        # Phat hien khuon mat
        faces = self.model_manager.detector(gray, 0)

        # Xu ly khi khong co khuon mat
        if len(faces) == 0:
            self.no_face_count += 1
            if self.no_face_count > self.config.NO_FACE_ALERT_FRAMES:
                self.alert_system.mode = "distracted"
                output = self.alert_system.render_distraction_alert(output)
        else:
            self.no_face_count = 0
            # Chon khuon mat lon nhat de xu ly
            face = max(faces, key=lambda rect: (rect.right() - rect.left()) * (rect.bottom() - rect.top()))

            # Phat hien landmarks va tinh toan chi so
            ear, mar, shape = self.process_face(gray, face, output)

            # Xu ly hieu chinh
            is_calibrating = self.handle_calibration(ear, output)

            if not is_calibrating:  # Sau khi hieu chinh
                # Logic phat hien ngu gat va cac tinh huong khac

                # 1. Phat hien chop mat va ngu gat
                if ear < self.config.EAR_THRESHOLD:
                    self.frame_count += 1
                    self.blink_counter += 1
                    self.eye_fatigue_frames += 1

                    # Kiem tra mat moi
                    if (self.eye_fatigue_frames >= self.config.EYE_FATIGUE_THRESHOLD and
                            not self.alert_system.eye_fatigue_alert_active):
                        self.alert_system.eye_fatigue_alert_active = True
                        self.alert_system.eye_fatigue_alert_start_time = time.time()

                    # Kiem tra ngu guc
                    if self.frame_count >= self.config.EAR_CONSEC_FRAMES:
                        self.alert_system.mode = "sleeping"
                        if self.alert_system.alert_start_time is None:
                            self.alert_system.alert_start_time = time.time()

                        alert_duration = int(current_time - self.alert_system.alert_start_time)
                        output = self.alert_system.render_drowsiness_alert(output, alert_duration)
                else:
                    # Reset canh bao ngu gat
                    if self.frame_count >= self.config.EAR_CONSEC_FRAMES:
                        self.alert_system.alert_start_time = None

                    # Kiem tra hoan thanh mot lan chop mat
                    if self.blink_counter >= self.config.BLINK_CONSEC_FRAMES:
                        if current_time - self.last_blink_time > 0.5:  # Dam bao khong dem lien tuc
                            self.blink_total += 1
                            self.last_blink_time = current_time

                    # Reset cac bien dem
                    self.frame_count = 0
                    self.blink_counter = 0
                    self.eye_fatigue_frames = 0  # Reset eye_fatigue_frames khi mat mo
                    self.alert_system.mode = "default"

                # Hien thi canh bao mat moi
                if (self.alert_system.eye_fatigue_alert_active and
                        self.alert_system.mode != "sleeping"):  # Khong hien thi khi dang co canh bao ngu gat
                    output = self.alert_system.render_fatigue_alert(output)

                    # Tu dong tat canh bao sau mot khoang thoi gian hoac khi mat mo lai
                    if (time.time() - self.alert_system.eye_fatigue_alert_start_time > 5.0 and
                            ear > self.config.EAR_THRESHOLD):
                        self.alert_system.eye_fatigue_alert_active = False

                # 2. Phat hien ngap
                if mar > self.config.MAR_THRESHOLD:
                    self.yawn_count += 1
                    if self.yawn_count >= 20:
                        if (self.alert_system.mode != "sleeping" and
                                not self.alert_system.eye_fatigue_alert_active):  # Uu tien canh bao ngu gat va mat moi
                            self.alert_system.mode = "drowsy"
                            output = self.alert_system.render_yawn_alert(output)
                else:
                    self.yawn_count = max(0, self.yawn_count - 1)

                # 3. Phat hien met moi dua vao tan so chop mat
                session_time = current_time - self.session_start_time
                if session_time > 30:  # Sau 30 giay theo doi
                    blink_frequency = self.blink_total / session_time  # Tan so chop mat (lan/giay)

                    # Tinh do dao dong cua EAR
                    ear_var = self.analyzer.eye_aspect_ratio_variance(list(self.ear_history))

                    # Phat hien met moi qua tan so chop mat cao hoac dao dong EAR thap
                    if (blink_frequency > self.config.BLINK_FREQUENCY_THRESHOLD or
                            (ear_var < self.config.EAR_VARIANCE_THRESHOLD and len(self.ear_history) > 100)):
                        if (self.alert_system.mode == "default" and
                                not self.alert_system.eye_fatigue_alert_active):  # Khong ghi de len cac canh bao nghiem trong hon
                            self.alert_system.mode = "tired"

                            # Hien thi dau hieu met moi
                            cv2.putText(output, "DAU HIEU MET MOI - NGHI NGOI!", (20, 120),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.config.SECONDARY_COLOR, 2)

                # Ve thanh trang thai EAR
                output = self.alert_system.render_status_bar(output, ear, self.config.EAR_THRESHOLD)

                # Hien thi chi so va trang thai
                status_text = f"Trang thai: {self.alert_system.mode.upper()}"
                if self.alert_system.eye_fatigue_alert_active:
                    status_text += " (MAT MOI)"

                metrics = [
                    f"EAR: {ear:.3f} (Nguong: {self.config.EAR_THRESHOLD:.3f})",
                    f"MAR: {mar:.3f}",
                    f"Chop mat: {self.blink_total} (Tan so: {self.blink_total / max(1, current_time - self.session_start_time):.2f}/giay)",
                    f"FPS: {self.fps:.1f}"
                ]

                output = self.alert_system.render_metrics(output, metrics, status_text)

        return output

    def run(self):
        """Chay he thong phat hien ngu gat"""
        print("Khoi tao he thong nhan dien...")
        self.start_camera()

        print("He thong da san sang. Nhan 'q' de thoat.")

        try:
            while True:
                output = self.process_frame()
                if output is None:
                    break

                # Hien thi frame
                cv2.imshow("He thong Phat hien Ngu gat", output)

                # Thoat khi nhan q
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except Exception as e:
            print(f"Loi trong qua trinh chay: {e}")

        finally:
            # Giai phong tai nguyen
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()
            print("Da thoat chuong trinh.")


if __name__ == "__main__":
    detector = DrowsinessDetector()
    detector.run()