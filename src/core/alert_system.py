import cv2
import numpy as np
import time
import threading
import logging
from PIL import Image, ImageDraw, ImageFont
from src.configs.config import Config

logger = logging.getLogger(__name__)

class AlertSystem:
    def __init__(self):
        # Khởi tạo hệ thống cảnh báo
        self.config = Config()
        self.alert_cooldown = self.config.ALERT_COOLDOWN
        self.last_alert_time = 0
        self.alert_start_time = None
        self._lock = threading.Lock()
        self._font_cache = {}  # Bộ nhớ đệm cho phông chữ

    def put_text_unicode(self, frame, text, position, color, font_size):
        """
        Vẽ văn bản tiếng Việt lên khung hình OpenCV bằng PIL.
        
        Args:
            frame: Khung hình OpenCV (numpy array, BGR).
            text: Văn bản cần vẽ (hỗ trợ tiếng Việt).
            position: Vị trí (x, y) để vẽ văn bản.
            color: Màu chữ (BGR, ví dụ: (255, 255, 255)).
            font_size: Kích thước phông chữ.
        
        Returns:
            Khung hình đã được vẽ văn bản.
        """
        # Chuyển khung hình OpenCV (BGR) sang PIL (RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(pil_image)

        # Tải phông chữ từ bộ nhớ đệm hoặc tệp
        if font_size not in self._font_cache:
            try:
                logger.info(f"Đang tải phông chữ từ: {self.config.FONT_PATH}")
                self._font_cache[font_size] = ImageFont.truetype(self.config.FONT_PATH, font_size)
            except Exception as e:
                logger.error(f"Không thể tải phông chữ {self.config.FONT_PATH}: {e}")
                self._font_cache[font_size] = ImageFont.load_default()
        
        font = self._font_cache[font_size]

        # Vẽ văn bản
        draw.text(position, text, font=font, fill=color[::-1])  # Chuyển BGR sang RGB

        # Chuyển lại sang định dạng OpenCV
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def render_drowsiness_alert(self, frame, duration=None):
        # Hiển thị cảnh báo buồn ngủ
        overlay = frame.copy()
        alpha = 0.4 + 0.2 * np.sin(time.time() * 8)  # Tạo hiệu ứng nhấp nháy
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), self.config.ALERT_COLOR, -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        alert_text = "CẢNH BÁO BUỒN NGỦ!"
        text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        text_x, text_y = (frame.shape[1] - text_size[0]) // 2, (frame.shape[0] + text_size[1]) // 2
        frame = self.put_text_unicode(frame, alert_text, (text_x, text_y), self.config.ALERT_COLOR, font_size=40)

        if duration:
            duration_text = f"Thời gian ngủ: {duration:.1f}s"
            frame = self.put_text_unicode(frame, duration_text, (20, 150), self.config.ALERT_COLOR, font_size=20)

        return frame

    def render_distraction_alert(self, frame):
        # Hiển thị cảnh báo mất tập trung
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), self.config.SECONDARY_COLOR, -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

        alert_text = "KHÔNG PHÁT HIỆN TÀI XẾ!"
        text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        frame = self.put_text_unicode(frame, alert_text, (text_x, 100), self.config.ALERT_COLOR, font_size=30)
        return frame

    def render_head_tilt_alert(self, frame):
        # Hiển thị cảnh báo nghiêng đầu
        overlay = frame.copy()
        alpha = 0.4 + 0.2 * np.sin(time.time() * 6)
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 165, 255), -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        alert_text = "CẢNH BÁO TƯ THẾ ĐẦU!"
        text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        frame = self.put_text_unicode(frame, alert_text, (text_x, frame.shape[0] // 2), (255, 255, 255), font_size=35)
        return frame

    def render_fatigue_alert(self, frame):
        # Hiển thị cảnh báo mệt mỏi mắt
        overlay = frame.copy()
        alpha = 0.4 + 0.3 * abs(np.sin(time.time() * 5))
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), self.config.ALERT_COLOR, -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        alert_text = "CẢNH BÁO MỆT MỎI MẮT!"
        text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
        text_x, text_y = (frame.shape[1] - text_size[0]) // 2, (frame.shape[0] + text_size[1]) // 2
        frame = self.put_text_unicode(frame, alert_text, (text_x, text_y), self.config.ALERT_COLOR, font_size=30)
        return frame

    def render_status_bar(self, frame, ear, ear_threshold):
        # Hiển thị thanh trạng thái EAR
        bar_length, bar_height = 150, 20
        filled_length = min(int(bar_length * (ear / 0.4)), bar_length)
        bar_x, bar_y = 20, 50
        bar_color = self.config.ALERT_COLOR if ear < ear_threshold else self.config.PRIMARY_COLOR
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_length, bar_y + bar_height), (50, 50, 50), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled_length, bar_y + bar_height), bar_color, -1)
        return frame

    def render_metrics(self, frame, metrics, status_text):
        # Hiển thị thông số và trạng thái
        frame = self.put_text_unicode(frame, status_text, (20, 30), self.config.TEXT_COLOR, font_size=20)
        for i, metric in enumerate(metrics):
            frame = self.put_text_unicode(frame, metric, (20, 80 + i * 20), self.config.TEXT_COLOR, font_size=20)
        return frame