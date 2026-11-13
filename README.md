# Manga Translator → Ukrainian

Translates manga, manhwa and manhua chapters from English, Korean or Chinese to Ukrainian. Paste a MangaDex chapter link, wait a few minutes, download the translated chapter as PDF or ZIP.

This is an MVP: it uses ready-made tools (EasyOCR + Gemini). The plan is to replace them with my own models later.

## How it works

```
MangaDex link
   → download pages          (download_chapter.py)
   → find text               (detect_ocr.py, EasyOCR)
   → translate to Ukrainian  (translate.py, Gemini API, it also sees the page image)
   → erase original text, draw Ukrainian text  (render.py, Pillow)
```

Each page has a JSON file with all text blocks:

```json
[{"box": [700, 534, 904, 582], "src": "PROMISE...", "uk": "обіцяю..."}]
```

All steps read and write this JSON. You can fix translations in the web editor and redraw the page.

## Setup

Tested on Ubuntu 24.04, Python 3.13. An NVIDIA GPU makes text detection faster, but it also works on CPU.

```bash
git clone https://github.com/Oriado/manga_translate.git
cd manga_translate
pip install -r requirements.txt
cp .env.example .env
```

Get a free Gemini API key at https://aistudio.google.com/apikey and put it into `.env`:

```
GEMINI_API_KEY=your_key_here
```

## Usage

### Web app (recommended)

```bash
uvicorn app:app
```

Open http://localhost:8000.

1. Go to https://mangadex.org, find a manga, open a chapter in English, Korean or Chinese.
2. Copy the address from the browser, for example `https://mangadex.org/chapter/df6bf737-1a2d-41b3-a0c2-30864c8f2e5a`.
3. Paste it into the field and press **Завантажити** (Download). Only the pages are downloaded, nothing is translated yet.
4. Check the source language (it is taken from MangaDex) and press **Перекласти** (Translate). Progress is shown on the page.
5. **Зупинити** (Stop) stops after the current page. **Перекласти / Продовжити переклад** continues; translated pages are skipped.
6. Click a translated page to fix the text, then press **Перемалювати** (Redraw).
7. Download the chapter as **PDF** or **ZIP** with JPG images. **Видалити розділ** (Delete) removes all its files.

The title and chapter number are taken from MangaDex. You can change them on the chapter page; PDF and ZIP files are named after them.

### Command line

```bash
python pipeline.py https://mangadex.org/chapter/<chapter-id>
```

Results are saved to `output/<chapter-id>/`.

## Where files are stored

- `input/<chapter-id>/`: original pages
- `data/<chapter-id>/`: JSON with text and translations for each page, `info.json` with the title
- `output/<chapter-id>/`: translated pages
- `exports/`: PDF and ZIP files

All these folders are in `.gitignore`.

## Settings

`config.py`:

- `TRANSLATOR`: which translator to use (now only `"gemini"`)
- `GEMINI_MODEL`: Gemini model name
- `FONT_PATH`: font for Ukrainian text (`Pangolin` and `Neucha` are in `fonts/`)
- `LANGUAGES`: supported source languages and EasyOCR language codes
- `BLOCKED_RATINGS`: MangaDex content ratings that are not allowed (empty by default)

## Known limitations

- **Gemini free tier allows only about 20 pages per day.** If the limit is reached, some pages stay untranslated. Press **Продовжити переклад** (Continue) the next day. Already translated pages are skipped.
- EasyOCR is not trained on manga, so it makes mistakes on handwritten fonts and sound effects.
- Text boxes cover only the original letters, not the whole speech bubble. Sometimes small parts of English text (dots) stay, and Ukrainian text can be small.
- Text on dark or colored backgrounds is covered with a white rectangle.
- Source languages: English (tested), Korean (OCR tested), Chinese (not tested yet). Japanese is not supported: EasyOCR can't read vertical text.
- The first run for a new language downloads an EasyOCR model (~100 MB).

## Plans

- Own speech bubble detector (YOLO)
- Own OCR trained on comic fonts
- Own translation model, more natural Ukrainian
- Japanese support (`manga-ocr`)
- Better editor: move and resize text on the page

## Fonts

Pangolin and Neucha are licensed under the SIL Open Font License (see `fonts/`).
