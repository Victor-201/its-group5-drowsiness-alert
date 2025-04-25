from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.slider import Slider
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Rectangle
import os
import logging
import cv2

class SettingsScreen(Screen):
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.build()

    def build(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Set up background color
        with layout.canvas.before:
            Color(*self.app.background_color)
            self.background_rect = Rectangle(pos=layout.pos, size=layout.size)
        
        # Bind update to layout size/position changes
        layout.bind(pos=self.update_background_rect, size=self.update_background_rect)

        # Camera selection
        camera_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.2))
        camera_layout.add_widget(Label(text='Camera:', size_hint=(0.3, 1)))
        self.camera_spinner = Spinner(
            text=f'Camera {self.app.settings.camera_index}',
            values=[f'Camera {cam}' for cam in self.app.settings.get_available_cameras()],
            size_hint=(0.7, 1)
        )
        camera_layout.add_widget(self.camera_spinner)
        layout.add_widget(camera_layout)

        # Volume control
        volume_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.2))
        volume_layout.add_widget(Label(text='Âm lượng:', size_hint=(0.3, 1)))
        self.volume_slider = Slider(min=0, max=100, value=self.app.settings.alert_volume, size_hint=(0.7, 1))
        volume_layout.add_widget(self.volume_slider)
        layout.add_widget(volume_layout)

        # Sound selection
        sound_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.2))
        sound_layout.add_widget(Label(text='Âm thanh:', size_hint=(0.3, 1)))
        self.sound_spinner = Spinner(
            text=self.app.settings.alert_sound_file or 'Mặc định',
            values=self.app.settings.get_available_sounds(),
            size_hint=(0.5, 1)
        )
        preview_button = Button(
            text='Nghe thử',
            size_hint=(0.2, 1),
            background_color=(0.5, 0.5, 1, 1),
            on_press=self.preview_sound
        )
        sound_layout.add_widget(self.sound_spinner)
        sound_layout.add_widget(preview_button)
        layout.add_widget(sound_layout)

        # Buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.2), spacing=10)
        save_button = Button(
            text='Lưu',
            size_hint=(0.5, 1),
            background_color=(0, 1, 0, 1),
            on_press=self.save_settings
        )
        back_button = Button(
            text='Quay lại',
            size_hint=(0.5, 1),
            background_color=(1, 0, 0, 1),
            on_press=lambda instance: self.app.switch_to_main()
        )
        button_layout.add_widget(save_button)
        button_layout.add_widget(back_button)
        layout.add_widget(button_layout)

        self.add_widget(layout)

    def update_background_rect(self, instance, value):
        self.background_rect.pos = instance.pos
        self.background_rect.size = instance.size

    def preview_sound(self, instance):
        selected_sound = self.sound_spinner.text
        if selected_sound == 'Mặc định':
            sound_path = self.app.alert_sound_file
        else:
            sound_path = os.path.join(self.app.sound_dir, selected_sound)
        
        if os.path.exists(sound_path):
            preview_sound = SoundLoader.load(sound_path)
            if preview_sound:
                preview_sound.volume = self.volume_slider.value / 100.0
                preview_sound.play()
                Clock.schedule_once(lambda dt: preview_sound.stop(), 3)
                logging.info(f"Phát thử âm thanh: {sound_path}")
            else:
                logging.warning(f"Không thể tải âm thanh để nghe thử: {sound_path}")
                self.app.status_label.text = "Lỗi: Không thể phát âm thanh"
        else:
            logging.warning(f"File âm thanh không tồn tại: {sound_path}")
            self.app.status_label.text = "Lỗi: File âm thanh không tồn tại"

    def save_settings(self, instance):
        try:
            # Get camera index
            selected_camera = self.camera_spinner.text
            new_camera_index = int(selected_camera.replace('Camera ', ''))
            
            # Test camera before saving
            test_cap = cv2.VideoCapture(new_camera_index)
            if not test_cap.isOpened():
                raise ValueError(f"Không thể truy cập Camera {new_camera_index}")
            test_cap.release()
            
            # Check if camera index has changed
            camera_changed = new_camera_index != self.app.settings.camera_index
            
            # Save camera settings
            self.app.settings.camera_index = new_camera_index
            
            # Save volume settings
            self.app.settings.alert_volume = int(self.volume_slider.value)
            
            # Save sound settings
            selected_sound = self.sound_spinner.text
            self.app.settings.alert_sound_file = selected_sound if selected_sound != 'Mặc định' else None
            
            # Save all settings
            self.app.settings.save()
            logging.info(f"Đã lưu cài đặt: Camera {new_camera_index}, Âm lượng {self.app.settings.alert_volume}%, Âm thanh {selected_sound}")
            
            # Update camera only if index changed
            if camera_changed and self.app.camera_initialized:
                self.app.detector.stop_camera()
                self.app.config.CAMERA_ID = new_camera_index
                self.app.detector.start_camera()
                logging.info(f"Chuyển sang camera {new_camera_index}")
            
            # Update alert sound
            self._update_alert_sound()
            
            self.app.switch_to_main()
            self.app.status_label.text = "Cài đặt đã được lưu"
            
        except ValueError as e:
            logging.error(f"Lỗi cài đặt camera: {e}")
            self.app.status_label.text = f"Lỗi: {str(e)}"
        except Exception as e:
            logging.error(f"Lỗi khi lưu cài đặt: {e}")
            self.app.status_label.text = "Lỗi: Không thể lưu cài đặt"

    def _update_alert_sound(self):
        selected_sound = self.sound_spinner.text
        sound_path = os.path.join(self.app.sound_dir, selected_sound) if selected_sound != 'Mặc định' else self.app.alert_sound_file
        if os.path.exists(sound_path):
            self.app.alert_sound = SoundLoader.load(sound_path)
            if self.app.alert_sound:
                self.app.alert_sound.volume = self.app.settings.alert_volume / 100.0
                logging.info(f"Đặt âm thanh cảnh báo: {sound_path}, âm lượng: {self.app.settings.alert_volume}%")
            else:
                logging.warning(f"Không thể tải file âm thanh: {sound_path}")
        else:
            logging.warning(f"File âm thanh không tồn tại: {sound_path}")
