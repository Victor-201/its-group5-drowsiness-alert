from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle

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
            ('Cài đặt', (0.5, 0.5, 0.5, 1), lambda instance: self.app.switch_to_settings())
        ]

        for text, color, callback in buttons:
            button = Button(
                text=text,
                size_hint=(0.2, 1),
                background_color=color,
                on_press=callback
            )
            header.add_widget(button)

        # Wrapper for camera feed
        wrapper = BoxLayout(size_hint=(1, 0.8))
        wrapper.add_widget(self.app.image)

        # Add components to main layout
        main_layout.add_widget(header)
        main_layout.add_widget(self.app.status_label)
        main_layout.add_widget(wrapper)

        self.add_widget(main_layout)

    def update_background_rect(self, instance, value):
        self.background_rect.pos = instance.pos
        self.background_rect.size = instance.size
