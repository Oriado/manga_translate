# Manga Translator → Ukrainian

Find a manga on MangaDex, read the original chapter and translate it from English to Ukrainian. The result can be downloaded as PDF.

**Live demo:** https://manga-translate-3s8p.onrender.com

This is an MVP built on ready-made tools (EasyOCR, Gemini). The plan is to replace them with my own models later.

## How it works

```
MangaDex API → download pages       (download_chapter.py, search.py)
             → find text            (detect_ocr.py: EasyOCR locally, Gemini on the server)
             → translate            (translate.py: Gemini, it also sees the page image)
             → draw Ukrainian text  (render.py: Pillow)
```

Every page has a JSON file with its text blocks. All steps read and write it:

```json
[{"box": [700, 534, 904, 582], "src": "PROMISE...", "uk": "обіцяю..."}]
```

## How to use

1. Search a manga by title.
2. Open it and choose an English chapter → **Відкрити**. You can read the pages or download **PDF оригіналу**.
3. Press **Перекласти українською**. A progress bar shows how far it is (about 20–40 s per page). You can leave the page, it keeps working.
4. Click a translated page to fix the text → **Перемалювати**.
5. Download **PDF українською**.

**Important:** on the free server files are temporary. They are deleted when the server restarts (after updates or 15 minutes without visitors). Download the PDF right after translating.

## Run locally

Tested on Ubuntu 24.04, Python 3.13. A GPU makes EasyOCR faster, but CPU works too.

```bash
git clone https://github.com/Oriado/manga_translate.git
cd manga_translate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app
```

Put a free Gemini key (https://aistudio.google.com/apikey) into `.env` and open http://localhost:8000. Locally files are kept in `input/`, `data/`, `output/` and `exports/`.

Command line: `python pipeline.py https://mangadex.org/chapter/<chapter-id>`

## Deploy on Render (free)

1. Sign in to https://render.com with GitHub.
2. **New → Blueprint**, choose this repo (it uses `render.yaml`).
3. Enter `GEMINI_API_KEY` → **Apply**.

The server uses Gemini instead of EasyOCR (`DETECTOR=gemini`), because EasyOCR needs ~2 GB of RAM and the free plan has 512 MB.

## Settings

In `config.py` or environment variables:

- `DETECTOR`: `easyocr` (default) or `gemini`
- `GEMINI_MODEL`: Gemini model
- `FONT_PATH`: font for Ukrainian text
- `SHOW_ADULT`: `0` hides 18+ titles

## Limitations

- Free Gemini allows about **20 pages per day**. When the limit is reached, the site says so; continue the next day, translated pages are kept.
- Only English chapters. Korean and Chinese exist in the code but are not tested.
- Sometimes small parts of the English text stay, and text on dark backgrounds gets a white rectangle.

## Plans

- Own speech bubble detector (YOLO), OCR and translation model
- Saving chapters permanently
- Better editor: move and resize text

## Fonts

Pangolin and Neucha, SIL Open Font License (see `fonts/`).
