import os

TRANSLATOR = "gemini"
GEMINI_MODEL = "gemini-2.5-flash"

FONT_PATH = "fonts/Pangolin-Regular.ttf"

LANGUAGES = {
      "en": {"name": "англійської", "ocr": ["en"]},
      "ko": {"name": "корейської", "ocr": ["ko", "en"]},
      "zh": {"name": "китайської", "ocr": ["ch_sim", "en"]},
}

BLOCKED_RATINGS = []

SHOW_ADULT = os.getenv("SHOW_ADULT", "1") == "1"
