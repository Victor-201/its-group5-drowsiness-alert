from kivy.lang import Builder

Builder.load_string('''
<RoundButton@Button>:
    background_normal: ''
    background_color: 0,0,0,0
    canvas.before:
        Color:
            rgba: (0.2, 0.6, 1, 1) if self.state == 'normal' else (0.1, 0.5, 0.9, 1)
        Ellipse:
            pos: self.pos
            size: self.size

<StyledLabel@Label>:
    color: 1, 1, 1, 1
    font_size: '16sp'
    
<MetricsPanel@BoxLayout>:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: 0.15, 0.15, 0.2, 0.9
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [15]
''')
