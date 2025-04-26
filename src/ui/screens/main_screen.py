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
    reverse_threshold = BooleanProperty(False)
    bar_color = ListProperty([0, 1, 0, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(value=self.update_bar, threshold=self.update_bar, angle=self.update_bar,
                  reverse_threshold=self.update_bar, size=self.update_bar, pos=self.update_bar)
        self.bar_length = 150
        self.bar_height = 20
        self.blink_state = 1.0
        self.update_bar()

    def update_bar(self, *args):
        self.canvas.clear()
        with self.canvas:
            bar_x = self.x + (self.width - self.bar_length) / 2
            bar_y = self.y + (self.height - self.bar_height) / 2
            if self.reverse_threshold:
                is_safe = self.value >= self.threshold
            else:
                is_safe = self.value < self.threshold
            if not is_safe:
                self.blink_state = 0.5 + 0.5 * abs(np.sin(time.time() * 5))
                self.bar_color = [1, 0, 0, self.blink_state]
            else:
                self.blink_state = 1.0
                self.bar_color = [0, 1, 0, 1]
            filled_length = min(int(self.bar_length * (self.value / self.max_value)),
                                self.bar_length) if self.max_value > 0 else 0
            Color(0.2, 0.2, 0.2, 1)
            Rectangle(pos=(bar_x, bar_y), size=(self.bar_length, self.bar_height))
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
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        with main_layout.canvas.before:
            Color(*self.app.background_color)
            self.background_rect = Rectangle(pos=main_layout.pos, size=main_layout.size)
        main_layout.bind(pos=self.update_background_rect, size=self.update_background_rect)
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
        content_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.8), spacing=10)
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
                'bar': StatusBar(value=0.0, max_value=50.0, threshold=30.0, size_hint=(1, 0.1))
            },
            'yawn_count': {
                'label': Label(
                    text='Ngáp: --',
                    size_hint=(1, 0.1),
                    font_size='20sp',
                    halign='left',
                    valign='middle',
                    text_size=(None, None),
                    padding_x=10
                ),
                'bar': StatusBar(value=0.0, max_value=50.0, threshold=30.0, size_hint=(1, 0.1))
            }
        }
        for metric in self.metrics_widgets.values():
            metrics_layout.add_widget(metric['label'])
            metrics_layout.add_widget(metric['bar'])
        content_layout.add_widget(metrics_layout)
        camera_layout = BoxLayout(size_hint=(0.7, 1))
        camera_layout.add_widget(self.app.image)
        content_layout.add_widget(camera_layout)
        main_layout.add_widget(header)
        main_layout.add_widget(self.app.status_label)
        main_layout.add_widget(content_layout)
        self.add_widget(main_layout)

    def update_background_rect(self, instance, value):
        self.background_rect.pos = instance.pos
        self.background_rect.size = instance.size

    def update_metrics(self, ear, mar, roll_angle, pitch_angle, blink_count, yawn_count=None):
        def safe_float(value, default=None):
            if value is None:
                return default
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
        is_alert = self.app.alert_active
        ear_value = safe_float(ear, None)
        self.metrics_widgets['ear']['label'].text = f'EAR: {ear:.2f}' if ear is not None else 'EAR: --'
        self.metrics_widgets['ear']['label'].color = [1, 0, 0,
                                                      1] if is_alert and ear is not None and ear_value < self.app.ear_threshold else [
            1, 1, 1, 1]
        if ear is not None:
            self.metrics_widgets['ear']['bar'].value = ear_value
        mar_value = safe_float(mar, None)
        self.metrics_widgets['mar']['label'].text = f'MAR: {mar:.2f}' if mar is not None else 'MAR: --'
        self.metrics_widgets['mar']['label'].color = [1, 0, 0,
                                                      1] if is_alert and mar is not None and mar_value > 0.5 else [1, 1,
                                                                                                                   1, 1]
        if mar is not None:
            self.metrics_widgets['mar']['bar'].value = mar_value
        roll_value = safe_float(roll_angle, None)
        self.metrics_widgets['roll_angle'][
            'label'].text = f'Góc nghiêng: {roll_angle:.1f}°' if roll_angle is not None else 'Góc nghiêng: --'
        self.metrics_widgets['roll_angle']['label'].color = [1, 0, 0,
                                                             1] if is_alert and roll_angle is not None and roll_value > 15.0 else [
            1, 1, 1, 1]
        if roll_angle is not None:
            self.metrics_widgets['roll_angle']['bar'].value = roll_value
        pitch_value = safe_float(pitch_angle, None)
        self.metrics_widgets['pitch_angle'][
            'label'].text = f'Góc cúi: {pitch_angle:.1f}°' if pitch_angle is not None else 'Góc cúi: --'
        self.metrics_widgets['pitch_angle']['label'].color = [1, 0, 0,
                                                              1] if is_alert and pitch_angle is not None and pitch_value > 15.0 else [
            1, 1, 1, 1]
        if pitch_angle is not None:
            self.metrics_widgets['pitch_angle']['bar'].value = pitch_value
        blink_value = safe_float(blink_count, 0)
        self.metrics_widgets['blink_count'][
            'label'].text = f'Nháy mắt: {int(blink_count)}' if blink_count is not None else 'Nháy mắt: 0'
        self.metrics_widgets['blink_count']['label'].color = [1, 0, 0,
                                                              1] if is_alert and self.app.detector.check_blink_frequency() else [
            1, 1, 1, 1]
        self.metrics_widgets['blink_count']['bar'].value = blink_value
        yawn_value = safe_float(yawn_count, 0)
        self.metrics_widgets['yawn_count'][
            'label'].text = f'Ngáp: {int(yawn_count)}' if yawn_count is not None else 'Ngáp: 0'
        self.metrics_widgets['yawn_count']['label'].color = [1, 0, 0,
                                                             1] if is_alert and self.app.detector.check_yawn_frequency() else [
            1, 1, 1, 1]
        self.metrics_widgets['yawn_count']['bar'].value = yawn_value