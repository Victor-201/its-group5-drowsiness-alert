# app.py
import os
import cv2
import logging
from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Rectangle
from kivy.core.audio import SoundLoader
from kivy.uix.screenmanager import ScreenManager
from src.core.detector import DrowsinessDetector
from src.configs.config import Config
from src.configs.settings import Settings
from src.ui.screens.main_screen import MainScreen
from src.ui.screens.settings_screen import SettingsScreen


logger = logging.getLogger(__name__)

class DrowsinessDetectorApp(App):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.detector = DrowsinessDetector()
        self.image = Image(size_hint=(1, 1))
        self.status_label = Label(text='Trạng thái: Đã dừng', size_hint=(1, 0.1))
        self.settings = Settings()
        self.sound_dir = self.config.SOUND_DIR  # Initialize sound_dir first
        self.alert_sound_file = self.config.ALERT_SOUND_FILE
        self.initialize_app()


    def initialize_app(self):
        self.camera_initialized = False
        self.alert_sound = None
        self.setup_alert_sound()
        self.setup_state_variables()

    def setup_alert_sound(self):
        default_sound = os.path.join(self.sound_dir, "alert.wav")
        sound_path = (
            os.path.join(self.sound_dir, self.settings.alert_sound_file) 
            if self.settings.alert_sound_file 
            else default_sound
        )
        if os.path.exists(sound_path):
            self.alert_sound = SoundLoader.load(sound_path)
            if not self.alert_sound:
                logging.warning(f"Không thể tải file âm thanh: {sound_path}")
        else:
            logging.warning(f"File âm thanh không tồn tại: {sound_path}")

    def setup_state_variables(self):
        self.is_monitoring = False
        self.alert_active = False
        self.alert_stop_timer = None
        self.alert_stop_delay = self.config.ALERT_STOP_DELAY
        self.calibration_event = None
        self.calibration_start_time = None
        self.background_color = [0, 0, 0, 1]
        self.screen_manager = None

    def build(self):
        self.screen_manager = ScreenManager()
        
        # Add Main Screen
        main_screen = MainScreen(app_instance=self, name='main')
        self.screen_manager.add_widget(main_screen)
        
        # Add Settings Screen
        settings_screen = SettingsScreen(name='settings', app_instance=self)
        self.screen_manager.add_widget(settings_screen)

        # Initialize camera
        try:
            self.detector.start_camera()
            self.camera_initialized = True
            logging.info("Khởi tạo camera thành công")
        except Exception as e:
            logging.error(f"Khởi tạo camera thất bại: {e}")
            self.status_label.text = 'Lỗi: Không khởi tạo được camera'

        # Schedule updates
        Clock.schedule_interval(self._update_wrapper, 1.0 / 30.0)
        return self.screen_manager

    def switch_to_settings(self):
        self.screen_manager.current = 'settings'
        logging.info("Chuyển sang màn hình cài đặt")

    def switch_to_main(self):
        self.screen_manager.current = 'main'
        logging.info("Chuyển về màn hình chính")

    def update_background_color(self):
        if self.screen_manager.current == 'main':
            main_screen = self.screen_manager.get_screen('main')
            with main_screen.canvas.before:
                Color(*self.background_color)
                main_screen.background_rect = Rectangle(pos=main_screen.pos, size=main_screen.size)

    def exit_app(self, instance):
        logging.info("Thoát ứng dụng")
        self.stop_monitoring(instance)
        App.get_running_app().stop()

    def _update_wrapper(self, dt):
        if self.is_monitoring and self.camera_initialized:
            self.update()
        elif self.calibration_event and self.camera_initialized:
            self.update_calibration(dt)

    def start_monitoring(self, instance):
        if not self.camera_initialized:
            self.status_label.text = 'Lỗi: Camera chưa khởi tạo'
            logging.error("Không thể bắt đầu giám sát: Camera chưa khởi tạo")
            return
        self.is_monitoring = True
        self.status_label.text = 'Trạng thái: Đang giám sát'
        self.background_color = [0, 0, 0, 1]  # Reset to black
        self.update_background_color()
        logging.info("Bắt đầu giám sát")

    def stop_monitoring(self, instance):
        self.is_monitoring = False
        self.alert_active = False
        self.status_label.text = 'Trạng thái: Đã dừng'
        self.image.texture = None
        if self.alert_stop_timer:
            self.alert_stop_timer.cancel()
            self.alert_stop_timer = None
            if self.alert_sound:
                self.alert_sound.stop()
        if self.calibration_event:
            self.calibration_event.cancel()
            self.calibration_event = None
        self.background_color = [0, 0, 0, 1]  # Reset to black
        self.update_background_color()
        logging.info("Dừng giám sát")

    def calibrate(self, instance):
        if not self.camera_initialized:
            self.status_label.text = 'Lỗi: Camera chưa khởi tạo'
            logging.error("Không thể hiệu chỉnh: Camera chưa khởi tạo")
            return
        self.is_monitoring = False
        self.status_label.text = 'Trạng thái: Đang hiệu chỉnh...'
        self.background_color = [0, 0, 0, 1]  # Reset to black
        self.update_background_color()
        logging.info("Bắt đầu hiệu chỉnh")
        self.detector.reset_calibration()
        self.calibration_start_time = Clock.get_time()
        self.calibration_event = Clock.schedule_interval(self.update_calibration, 1.0 / 30.0)

    def update_calibration(self, dt):
        duration = 5
        elapsed = Clock.get_time() - self.calibration_start_time
        if elapsed >= duration:
            success, new_threshold = self.detector.finalize_calibration()
            self.calibration_event.cancel()
            self.calibration_event = None
            self.status_label.text = f'Trạng thái: Hiệu chỉnh hoàn tất (EAR: {new_threshold:.3f})' if success else 'Trạng thái: Hiệu chỉnh thất bại'
            logging.info(f"Hiệu chỉnh {'hoàn tất' if success else 'thất bại'}. Ngưỡng EAR mới: {new_threshold:.3f}" if success else "Hiệu chỉnh thất bại")
            self.image.texture = None
            self.background_color = [0, 0, 0, 1]  # Reset to black
            self.update_background_color()
            return
        frame, ear = self.detector.process_calibration_frame()
        if frame is not None:
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(cv2.flip(frame, 0).tobytes(), colorfmt='bgr', bufferfmt='ubyte')
            self.image.texture = texture
            remaining = int(duration - elapsed)
            self.status_label.text = f'Đang hiệu chỉnh... {remaining}s (EAR: {ear:.2f})'

    def update(self):
        try:
            frame, drowsiness_detected = self.detector.process_frame()
            if frame is not None:
                texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
                texture.blit_buffer(cv2.flip(frame, 0).tobytes(), colorfmt='bgr', bufferfmt='ubyte')
                self.image.texture = texture

                if drowsiness_detected and not self.alert_active:
                    self.status_label.text = 'CẢNH BÁO: Phát hiện buồn ngủ!'
                    self.alert_active = True
                    self.background_color = [1, 0, 0, 1]  # Red for alert
                    self.update_background_color()
                    logging.info("Phát hiện buồn ngủ")
                    self.start_alert()
                elif not drowsiness_detected and self.alert_active and not self.alert_stop_timer:
                    self.alert_stop_timer = Clock.schedule_once(self.stop_alert, self.alert_stop_delay)
                elif not self.alert_active:
                    self.status_label.text = 'Trạng thái: Đang giám sát'
                    self.background_color = [0, 0, 0, 1]  # Black when no alert
                    self.update_background_color()
        except Exception as e:
            logging.error(f"Lỗi xử lý khung hình: {e}")
            self.status_label.text = 'Lỗi: Xử lý khung hình thất bại'
            self.background_color = [0, 0, 0, 1]  # Reset to black
            self.update_background_color()

    def start_alert(self):
        logging.info("Bắt đầu phát âm thanh cảnh báo")
        self.alert_active = True
        if self.alert_sound:
            self.alert_sound.stop()
            self.alert_sound.loop = True
            self.alert_sound.volume = self.settings.alert_volume / 100.0
            self.alert_sound.play()
        self.background_color = [1, 0, 0, 1]  # Red for alert
        self.update_background_color()
        if self.alert_stop_timer:
            self.alert_stop_timer.cancel()
            self.alert_stop_timer = None

    def stop_alert(self, dt):
        self.alert_active = False
        if self.alert_sound:
            self.alert_sound.stop()
        self.alert_stop_timer = None
        self.status_label.text = 'Trạng thái: Đang giám sát'
        self.background_color = [0, 0, 0, 1]  # Reset to black
        self.update_background_color()
        logging.info("Dừng cảnh báo")

    def on_stop(self):
        logging.info("Dọn dẹp tài nguyên")
        if self.alert_stop_timer:
            self.alert_stop_timer.cancel()
        if self.alert_sound:
            self.alert_sound.stop()
        if self.calibration_event:
            self.calibration_event.cancel()
        self.detector.stop_camera()
        self.background_color = [0, 0, 0, 1]  # Reset to black
        self.update_background_color()