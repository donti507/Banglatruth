from langdetect import detect, LangDetectException

def detect_language(text):
    try:
        lang = detect(text)
        return lang
    except LangDetectException:
        return "unknown"

def get_language_name(lang_code):
    languages = {
        "en": "English",
        "bn": "Bangla",
        "ar": "Arabic",
        "hi": "Hindi",
        "ur": "Urdu",
    }
    return languages.get(lang_code, "Unknown language")