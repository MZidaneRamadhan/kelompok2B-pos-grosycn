class Theme:

    # GLOBAL SETTINGS
    FONT_SIZE = 16

    RADIUS = 8

    FONT_WEIGHT_MEDIUM = 500
    FONT_WEIGHT_NORMAL = 400

    # LIGHT MODE (default)
    LIGHT = {
        "background": "#ffffff",
        "foreground": "#242424",

        "card": "#ffffff",
        "card_foreground": "#242424",

        "popover": "#ffffff",
        "popover_foreground": "#242424",

        "primary": "#4f46e5",
        "primary_foreground": "#ffffff",

        "secondary": "#f2f2f7",
        "secondary_foreground": "#030213",

        "muted": "#ececf0",
        "muted_foreground": "#717182",

        "accent": "#e9ebef",
        "accent_foreground": "#030213",

        "destructive": "#d4183d",
        "destructive_foreground": "#ffffff",

        "success": "#10b981",
        "success_foreground": "#ffffff",

        "warning": "#f59e0b",
        "warning_foreground": "#ffffff",

        "border": "rgba(0, 0, 0, 0.1)",
        "input": "transparent",
        "input_background": "#f3f3f5",
        "switch_background": "#cbced4",

        "ring": "#b3b3b3",

        "chart_1": "#4f46e5",
        "chart_2": "#10b981",
        "chart_3": "#f59e0b",
        "chart_4": "#8b5cf6",
        "chart_5": "#ec4899",

        "sidebar": "#f9fafb",
        "sidebar_foreground": "#1f2937",
        "sidebar_primary": "#4f46e5",
        "sidebar_primary_foreground": "#ffffff",
        "sidebar_accent": "#f3f4f6",
        "sidebar_accent_foreground": "#1f2937",
        "sidebar_border": "#e5e7eb",
        "sidebar_ring": "#b3b3b3",
    }

    # DARK MODE
    DARK = {
        "background": "#0f1117",
        "foreground": "#f9fafb",

        "card": "#1a1c24",
        "card_foreground": "#f9fafb",

        "popover": "#1a1c24",
        "popover_foreground": "#f9fafb",

        "primary": "#6366f1",
        "primary_foreground": "#ffffff",

        "secondary": "#2a2d3a",
        "secondary_foreground": "#f9fafb",

        "muted": "#2a2d3a",
        "muted_foreground": "#9ca3af",

        "accent": "#2a2d3a",
        "accent_foreground": "#f9fafb",

        "destructive": "#ef4444",
        "destructive_foreground": "#ffffff",

        "success": "#10b981",
        "success_foreground": "#ffffff",

        "warning": "#f59e0b",
        "warning_foreground": "#ffffff",

        "border": "#2a2d3a",
        "input": "#2a2d3a",
        "ring": "#4b5563",

        "chart_1": "#6366f1",
        "chart_2": "#10b981",
        "chart_3": "#f59e0b",
        "chart_4": "#8b5cf6",
        "chart_5": "#ec4899",

        "sidebar": "#1a1c24",
        "sidebar_foreground": "#f9fafb",
        "sidebar_primary": "#6366f1",
        "sidebar_primary_foreground": "#ffffff",
        "sidebar_accent": "#2a2d3a",
        "sidebar_accent_foreground": "#f9fafb",
        "sidebar_border": "#2a2d3a",
        "sidebar_ring": "#4b5563",
    }

    # ======================
    # ACTIVE THEME
    # ======================
    mode = "light"

    @classmethod
    def colors(cls):
        return cls.DARK if cls.mode == "dark" else cls.LIGHT

    # 👉 Tempat semua warna / theme disimpan
    # supaya konsisten di seluruh aplikasi
    DARK_THEME = {
        "sidebar": "#2c3e50",
        "sidebar_button": "#34495e",
        "sidebar_hover": "#1abc9c",
        "topbar": "#ecf0f1",
    }

