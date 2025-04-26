import numpy as np
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, PushMatrix, Rotate, PopMatrix
from kivy.properties import NumericProperty, ListProperty, BooleanProperty
import time


class StatusBar(Widget):
    value = NumericProperty(0.0)
    max_value = NumericProperty(1.0)
    threshold = NumericProperty(0.0)
    angle = NumericProperty(0.0)
    reverse_threshold = BooleanProperty(False)  # For EAR
    bar_color = ListProperty([0, 1, 0, 1])  # Default green

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(value=self.update_bar, threshold=self.update_bar, angle=self.update_bar,
                  reverse_threshold=self.update_bar, size=self.update_bar, pos=self.update_bar)
        self.bar_length = 150
        self.bar_height = 20
        self.blink_state = 1.0  # For blinking effect
        self.update_bar()

    def update_bar(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Center the bar horizontally
            bar_x = self.x + (self.width - self.bar_length) / 2
            bar_y = self.y + (self.height - self.bar_height) / 2

            # Update color based on threshold and reverse_threshold
            if self.reverse_threshold:
                is_safe = self.value >= self.threshold
            else:
                is_safe = self.value < self.threshold

            # Apply blinking effect if not safe (alert condition)
            if not is_safe:
                self.blink_state = 0.5 + 0.5 * abs(np.sin(time.time() * 5))  # Blinking frequency
                self.bar_color = [1, 0, 0, self.blink_state]  # Red with blinking opacity
            else:
                self.blink_state = 1.0
                self.bar_color = [0, 1, 0, 1]  # Green if safe

            # Calculate filled length based on value ratio
            filled_length = min(int(self.bar_length * (self.value / self.max_value)),
                                self.bar_length) if self.max_value > 0 else 0

            # Draw background bar
            Color(0.2, 0.2, 0.2, 1)  # Dark gray
            Rectangle(pos=(bar_x, bar_y), size=(self.bar_length, self.bar_height))

            # Draw filled bar with rotation
            Color(*self.bar_color)
            PushMatrix()
            Rotate(angle=self.angle, origin=(bar_x + self.bar_length / 2, bar_y + self.bar_height / 2))
            Rectangle(pos=(bar_x, bar_y), size=(filled_length, self.bar_height))
            PopMatrix()


class MainScreen(Screen):
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.build()

    def build(self):
        # Main layout (vertical)
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Set up background color
        with main_layout.canvas.before:
            Color(*self.app.background_color)
            self.background_rect = Rectangle(pos=main_layout.pos, size=main_layout.size)

        main_layout.bind(pos=self.update_background_rect, size=self.update_background_rect)

        # Header layout for buttons
        header = BoxLayout(size_hint=(1, 0.1), spacing=10)

        buttons = [
            ('Thoát', (1, 0, 0, 1), self.app.exit_app),
            ('Bắt đầu', (0, 1, 0, 1), self.app.start_monitoring),
            ('Dừng', (1, 0.5, 0, 1), self.app.stop_monitoring),
            ('Hiệu chỉnh', (0, 0, 1, 1), self.app.calibrate),
            ('Cài đặt', (0.5, 0.5, 0.5, 1), lambda instance: self.app.switch_to_settings(instance))
        ]

        for text, color, callback in buttons:
            button = Button(
                text=text,
                size_hint=(0.2, 1),
                background_color=color,
                on_press=callback
            )
            header.add_widget(button)

        # Main content area (horizontal layout for camera and metrics)
        content_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.8), spacing=10)

        # Left side: Metrics display
        metrics_layout = BoxLayout(orientation='vertical', size_hint=(0.3, 1), spacing=5)
        self.metrics_widgets = {
            'ear': {
                'label': Label(
                    text='EAR: --',
                    size_hint=(1, 0.1),
                    font_size='20sp',
                    halign='left',
                    valign='middle',
                    text_size=(None, None),
                    padding_x=10
                ),
                'bar': StatusBar(value=0.0, max_value=0.4, threshold=self.app.ear_threshold, reverse_threshold=True,
                                 size_hint=(1, 0.1))
            },
            'mar': {
                'label': Label(
                    text='MAR: --',
                    size_hint=(1, 0.1),
                    font_size='20sp',
                    halign='left',
                    valign='middle',
                    text_size=(None, None),
                    padding_x=10
                ),
                'bar': StatusBar(value=0.0, max_value=1.0, threshold=0.5, size_hint=(1, 0.1))
            },
            'roll_angle': {
                'label': Label(
                    text='Góc nghiêng: --',
                    size_hint=(1, 0.1),
                    font_size='20sp',
                    halign='left',
                    valign='middle',
                    text_size=(None, None),
                    padding_x=10
                ),
                'bar': StatusBar(value=0.0, max_value=45.0, threshold=15.0, size_hint=(1, 0.1))
            },
            'pitch_angle': {
                'label': Label(
                    text='Góc cúi: --',
                    size_hint=(1, 0.1),
                    font_size='20sp',
                    halign='left',
                    valign='middle',
                    text_size=(None, None),
                    padding_x=10
                ),
                'bar': StatusBar(value=0.0, max_value=45.0, threshold=15.0, size_hint=(1, 0.1))
            },
            'blink_count': {
                'label': Label(
                    text='Nháy mắt: --',
                    size_hint=(1, 0.1),
                    font_size='20sp',
                    halign='left',
                    valign='middle',
                    text_size=(None, None),
                    padding_x=10
                ),
                'bar': StatusBar(value=0.0, max_value=10.0, threshold=5.0, size_hint=(1, 0.1))
            }
        }
        for metric in self.metrics_widgets.values():
            metrics_layout.add_widget(metric['label'])
            metrics_layout.add_widget(metric['bar'])
        content_layout.add_widget(metrics_layout)

        # Right side: Camera feed
        camera_layout = BoxLayout(size_hint=(0.7, 1))
        camera_layout.add_widget(self.app.image)
        content_layout.add_widget(camera_layout)

        # Add components to main layout
        main_layout.add_widget(header)
        main_layout.add_widget(self.app.status_label)
        main_layout.add_widget(content_layout)

        self.add_widget(main_layout)

    def update_background_rect(self, instance, value):
        self.background_rect.pos = instance.pos
        self.background_rect.size = instance.size

    def update_metrics(self, ear, mar, roll_angle, pitch_angle, blink_count):
        """Cập nhật các thông số và thanh trạng thái trên giao diện."""

        def safe_float(value, default=None):
            if value is None:
                return default
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        # Check if an alert is active
        is_alert = self.app.alert_active

        # Update EAR
        ear_value = safe_float(ear, None)  # Use None to retain last bar value
        self.metrics_widgets['ear']['label'].text = f'EAR: {ear:.2f}' if ear is not None else 'EAR: --'
        self.metrics_widgets['ear']['label'].color = [1, 0, 0,
                                                      1] if is_alert and ear is not None and ear_value < self.app.ear_threshold else [
            1, 1, 1, 1]
        if ear is not None:
            self.metrics_widgets['ear']['bar'].value = ear_value

        # Update MAR
        mar_value = safe_float(mar, None)
        self.metrics_widgets['mar']['label'].text = f'MAR: {mar:.2f}' if mar is not None else 'MAR: --'
        self.metrics_widgets['mar']['label'].color = [1, 0, 0,
                                                      1] if is_alert and mar is not None and mar_value > 0.5 else [1, 1,
                                                                                                                   1, 1]
        if mar is not None:
            self.metrics_widgets['mar']['bar'].value = mar_value

        # Update Roll Angle
        roll_value = safe_float(roll_angle, None)
        self.metrics_widgets['roll_angle'][
            'label'].text = f'Góc nghiêng: {roll_angle:.1f}°' if roll_angle is not None else 'Góc nghiêng: --'
        self.metrics_widgets['roll_angle']['label'].color = [1, 0, 0,
                                                             1] if is_alert and roll_angle is not None and roll_value > 15.0 else [
            1, 1, 1, 1]
        if roll_angle is not None:
            self.metrics_widgets['roll_angle']['bar'].value = roll_value

        # Update Pitch Angle
        pitch_value = safe_float(pitch_angle, None)
        self.metrics_widgets['pitch_angle'][
            'label'].text = f'Góc cúi: {pitch_angle:.1f}°' if pitch_angle is not None else 'Góc cúi: --'
        self.metrics_widgets['pitch_angle']['label'].color = [1, 0, 0,
                                                              1] if is_alert and pitch_angle is not None and pitch_value > 15.0 else [
            1, 1, 1, 1]
        if pitch_angle is not None:
            self.metrics_widgets['pitch_angle']['bar'].value = pitch_value

        # Update Blink Count
        blink_value = safe_float(blink_count, None)
        self.metrics_widgets['blink_count'][
            'label'].text = f'Nháy mắt: {blink_count}' if blink_count is not None else 'Nháy mắt: --'
        self.metrics_widgets['blink_count']['label'].color = [1, 0, 0,
                                                              1] if is_alert and blink_count is not None and blink_value > 5.0 else [
            1, 1, 1, 1]
        if blink_count is not None:
            self.metrics_widgets['blink_count']['bar'].value = blink_value