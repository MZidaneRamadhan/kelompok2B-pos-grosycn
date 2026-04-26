from views.styles.palettes import DARK_THEME


class ThemeManager:
    # 👉 central control untuk styling

    @staticmethod
    def apply_sidebar(widget):
        widget.setStyleSheet(f"""
            background-color: {DARK_THEME['sidebar']};
            color: white;
        """)

    @staticmethod
    def apply_button(button):
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DARK_THEME['sidebar_button']};
                padding: 10px;
                border: none;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {DARK_THEME['sidebar_hover']};
            }}
        """)