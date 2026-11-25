import os
import json
import time
import shutil
from html import escape
from PIL import Image
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from download_chapter import get_chapter_id, get_chapter_details, download_chapter
from pipeline import process_page
from render import render_page
from search import search_manga, get_manga, get_chapters, get_cover_image
import config
import translate as translate_module

os.makedirs("input", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("exports", exist_ok=True)

app = FastAPI()
app.mount("/input", StaticFiles(directory="input"), name="input")
app.mount("/output", StaticFiles(directory="output"), name="output")

status = {}
stop = set()
progress = {}

style = """
<!DOCTYPE html>
<html lang="uk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="only light">
<title>Manga Translator</title>
<style>
* { box-sizing: border-box; }
html { background: #f4f4f6; min-height: 100%; color-scheme: only light; }
body { font-family: system-ui, sans-serif; margin: 0; background: #f4f4f6; color: #222; min-height: 100vh; }
header { background: #1e1e2e; padding: 14px 30px; display: flex; gap: 24px; align-items: center; }
header a { color: #ddd; text-decoration: none; font-size: 16px; }
header .logo { color: white; font-weight: bold; font-size: 20px; margin-right: 20px; }
main { max-width: 1200px; margin: 25px auto; padding: 25px 30px; background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
h1 { margin-top: 5px; }
a { color: #4a3aff; }
input[type=text] { width: 100%; max-width: 600px; padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 8px; }
select { padding: 10px; font-size: 16px; border-radius: 8px; border: 1px solid #ccc; }
textarea { width: 100%; max-width: 700px; font-size: 15px; padding: 8px; border-radius: 6px; border: 1px solid #ccc; }
button, .button { display: inline-block; padding: 11px 20px; font-size: 15px; background: #4a3aff; color: white; border: none; border-radius: 8px; text-decoration: none; cursor: pointer; margin: 3px 0; }
button:hover, .button:hover { opacity: 0.85; }
.gray { background: #555; }
.red { background: #c0392b; }
.hero { text-align: center; padding: 50px 20px 30px; }
.hero input[type=text] { max-width: 750px; padding: 15px; font-size: 18px; }
.hero button { padding: 15px 28px; font-size: 17px; }
.plain { background: transparent; box-shadow: none; }
.box { background: white; border-radius: 12px; padding: 20px 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); margin-top: 20px; }
.outline { background: white; color: #4a3aff; border: 1px solid #4a3aff; }
.bar { width: 100%; height: 22px; background: #e4e4ee; border-radius: 11px; overflow: hidden; margin: 10px 0; }
.bar div { height: 100%; background: #4a3aff; transition: width 0.5s; }
.hero form { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
.status { background: #eef; padding: 12px 16px; border-radius: 8px; font-weight: bold; }
.pages { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 20px; }
.pages a, .pages div { width: 170px; text-align: center; color: #222; text-decoration: none; font-size: 13px; }
.pages img { width: 170px; border-radius: 6px; border: 1px solid #ddd; }
.hint { color: #666; }
.error { color: #c0392b; font-weight: bold; }
.grid { display: flex; flex-wrap: wrap; gap: 18px; }
.card { width: 170px; color: #222; text-decoration: none; font-size: 14px; font-weight: 600; }
.card img { width: 170px; height: 245px; object-fit: cover; border-radius: 8px; background: #ddd; transition: transform 0.15s; }
.card:hover img { transform: scale(1.04); }
table { border-collapse: collapse; width: 100%; }
td { padding: 8px 12px; border-bottom: 1px solid #eee; }
tr:hover { background: #fafafa; }
</style></head><body>
<header><a class="logo" href="/">📖 Manga Translator</a><a href="/">Пошук</a><a href="/#my">Мої розділи</a></header>
<main>
"""


def find_image(chapter, name):
      for page in os.listdir("input/" + chapter):
            if page.split(".")[0] == name:
                  return "input/" + chapter + "/" + page


def read_info(chapter):
      path = "data/" + chapter + "/info.json"
      if not os.path.exists(path):
            return {"title": chapter, "chapter": "?", "language": "en", "rating": "?"}
      with open(path, "r", encoding="utf-8") as file:
            return json.load(file)


def file_name(chapter):
      info = read_info(chapter)
      name = info["title"] + " - розділ " + str(info["chapter"])
      for symbol in '/\\:*?"<>|':
            name = name.replace(symbol, "")
      return name


def is_working(chapter):
      text = status.get(chapter, "")
      return text.startswith("Перекладаю") or text.startswith("Завантажую") or text.startswith("Зупиняю")


def download_task(chapter_id):
      try:
            status[chapter_id] = "Завантажую сторінки з MangaDex..."
            download_chapter(chapter_id)
            status[chapter_id] = "Сторінки завантажено. Натисніть «Перекласти», щоб почати."
      except Exception as error:
            status[chapter_id] = "Помилка: " + str(error)


def translate_task(chapter_id, lang):
      try:
            stop.discard(chapter_id)
            pages = sorted(os.listdir("input/" + chapter_id))
            failed = 0
            for i in range(len(pages)):
                  progress[chapter_id] = [i, len(pages)]
                  if chapter_id in stop:
                        status[chapter_id] = "Зупинено. Перекладені сторінки збережено, натисніть «Перекласти», щоб продовжити."
                        return
                  status[chapter_id] = "Перекладаю сторінку " + str(i + 1) + " з " + str(len(pages))
                  if not process_page(chapter_id, pages[i], lang):
                        failed = failed + 1
                        if translate_module.last_error == 429:
                              status[chapter_id] = "Денний ліміт перекладу вичерпано (безкоштовний Gemini: ~20 сторінок на день). Перекладені сторінки збережено, продовжіть завтра."
                              return

            progress[chapter_id] = [len(pages), len(pages)]
            if failed > 0:
                  status[chapter_id] = "Готово, але " + str(failed) + " сторінок не вдалося перекласти (сервер Gemini перевантажений). Натисніть «Перекласти» ще раз пізніше."
            else:
                  status[chapter_id] = "Готово! Можна завантажити PDF українською."
      except Exception as error:
            status[chapter_id] = "Помилка: " + str(error)


@app.get("/", response_class=HTMLResponse)
def index(error: str = ""):
      html = style.replace("<main>", '<main class="plain">')
      working = any(is_working(chapter) for chapter in status)
      if working:
            html += '<meta http-equiv="refresh" content="5">'
      html += '<div class="hero"><h1>Переклад манги українською</h1>'
      html += '<p>Манга береться з <a href="https://mangadex.org" target="_blank">MangaDex</a>. Перекладаються розділи англійською.</p>'
      html += '<form method="get" action="/search">'
      html += '<input type="text" name="q" placeholder="Назва манги англійською або японською, наприклад City Hunter"> '
      html += '<button type="submit">Шукати</button>'
      if config.SHOW_ADULT:
            html += '<br><label><input type="checkbox" name="adult" value="1"> показувати 18+</label>'
      html += '</form>'
      html += '<p class="hint">1. Знайдіть мангу → 2. Відкрийте розділ і перегляньте оригінал → 3. Перекладіть і завантажте PDF</p>'
      if error != "":
            html += '<p class="error">' + escape(error) + '</p>'
      html += '<details style="margin-top:20px"><summary class="hint">Маєте посилання на розділ MangaDex?</summary><br>'
      html += '<form method="post" action="/start">'
      html += '<input type="text" name="link" placeholder="https://mangadex.org/chapter/..."> '
      html += '<button class="outline" type="submit">Відкрити розділ</button></form></details></div>'

      chapters = sorted(os.listdir("input"))
      if len(chapters) > 0:
            html += '<div class="box"><h2 id="my">Мої розділи</h2>'
            for chapter in chapters:
                  info = read_info(chapter)
                  html += '<p><a href="/chapter/' + chapter + '">' + escape(info["title"]) + ', розділ ' + escape(str(info["chapter"])) + '</a> '
                  html += '<span class="hint">' + escape(status.get(chapter, "")) + '</span></p>'
            html += '</div>'
      return html


@app.get("/search", response_class=HTMLResponse)
def search(q: str = "", adult: str = ""):
      results = search_manga(q, adult == "1" and config.SHOW_ADULT)

      html = style + '<a href="/">← на головну</a><h1>Пошук: ' + escape(q) + '</h1>'
      if len(results) == 0:
            html += "<p>Нічого не знайдено.</p>"
      html += '<div class="grid">'
      for manga in results:
            cover = ""
            if manga["cover"]:
                  cover = '/cover/' + manga["id"] + '/' + manga["cover"]
            html += '<a class="card" href="/manga/' + manga["id"] + '"><img src="' + cover + '"><br>' + escape(manga["title"]) + '</a>'
      html += '</div>'
      return html


@app.get("/cover/{manga_id}/{file_name}")
def cover(manga_id, file_name):
      return Response(get_cover_image(manga_id, file_name), media_type="image/jpeg")


@app.get("/manga/{manga_id}", response_class=HTMLResponse)
def manga_page(manga_id, lang: str = "en", offset: int = 0):
      manga = get_manga(manga_id)
      if not config.SHOW_ADULT and manga["rating"] in ["erotica", "pornographic"]:
            return RedirectResponse("/?error=Цей тайтл 18+, на цьому сайті він недоступний", status_code=303)
      chapters, total = get_chapters(manga_id, lang, offset)

      html = style + '<a href="/">← на головну</a>'
      html += '<div style="display:flex; gap:20px; margin-top:15px">'
      if manga["cover"]:
            html += '<img src="/cover/' + manga_id + '/' + manga["cover"] + '" style="width:200px; border-radius:6px">'
      html += '<div><h1>' + escape(manga["title"]) + '</h1><p>' + escape(manga["description"][:600]) + '</p>'
      html += '<a href="https://mangadex.org/title/' + manga_id + '" target="_blank">Відкрити на MangaDex ↗</a></div></div>'
      html += '<h2>Розділи англійською</h2>'

      if len(chapters) == 0:
            html += "<p>Англійських розділів для перекладу немає. Деякі розділи на MangaDex доступні лише на сторонніх сайтах, їх завантажити не можна.</p>"
      html += '<table>'
      for chapter in chapters:
            name = "Розділ " + str(chapter["number"])
            if chapter["title"]:
                  name += ": " + chapter["title"]
            html += '<tr><td>' + escape(name) + '</td><td>' + str(chapter["pages"]) + ' стор.</td><td>'
            html += '<form method="post" action="/start" style="margin:0"><input type="hidden" name="link" value="' + chapter["id"] + '">'
            html += '<button type="submit">Відкрити</button></form></td></tr>'
      html += '</table>'

      if offset > 0:
            html += '<a href="/manga/' + manga_id + '?lang=' + lang + '&offset=' + str(max(0, offset - 100)) + '">← попередні</a> '
      if offset + 100 < total:
            html += '<a href="/manga/' + manga_id + '?lang=' + lang + '&offset=' + str(offset + 100) + '">наступні →</a>'
      return html


@app.post("/start")
async def start(request: Request, background_tasks: BackgroundTasks):
      form = await request.form()
      chapter_id = get_chapter_id(form["link"])
      if chapter_id is None:
            return RedirectResponse("/?error=Це не схоже на посилання на розділ MangaDex", status_code=303)

      try:
            info = get_chapter_details(chapter_id)
      except Exception:
            return RedirectResponse("/?error=Не вдалося знайти цей розділ на MangaDex", status_code=303)

      if info["language"] != "en":
            return RedirectResponse("/?error=Підтримуються лише розділи англійською", status_code=303)

      if not config.SHOW_ADULT and info["rating"] in ["erotica", "pornographic"]:
            return RedirectResponse("/?error=Цей тайтл 18+, на цьому сайті він недоступний", status_code=303)

      if info["rating"] in config.BLOCKED_RATINGS:
            return RedirectResponse("/?error=Цей тайтл 18+ (" + info["rating"] + "), він заблокований у config.py", status_code=303)

      os.makedirs("data/" + chapter_id, exist_ok=True)
      with open("data/" + chapter_id + "/info.json", "w", encoding="utf-8") as file:
            json.dump(info, file, ensure_ascii=False, indent=2)

      if not is_working(chapter_id):
            status[chapter_id] = "Завантажую сторінки з MangaDex..."
            background_tasks.add_task(download_task, chapter_id)
      return RedirectResponse("/chapter/" + chapter_id, status_code=303)


@app.post("/chapter/{chapter}/translate")
async def translate(chapter, request: Request, background_tasks: BackgroundTasks):
      form = await request.form()
      lang = form.get("lang", "en")
      if not is_working(chapter):
            status[chapter] = "Перекладаю..."
            background_tasks.add_task(translate_task, chapter, lang)
      return RedirectResponse("/chapter/" + chapter, status_code=303)


@app.post("/chapter/{chapter}/rename")
async def rename(chapter, request: Request):
      form = await request.form()
      info = read_info(chapter)
      info["title"] = form["title"].strip()
      info["chapter"] = form["number"].strip()
      os.makedirs("data/" + chapter, exist_ok=True)
      with open("data/" + chapter + "/info.json", "w", encoding="utf-8") as file:
            json.dump(info, file, ensure_ascii=False, indent=2)
      return RedirectResponse("/chapter/" + chapter, status_code=303)


@app.post("/chapter/{chapter}/stop")
def stop_translate(chapter):
      stop.add(chapter)
      status[chapter] = "Зупиняю після поточної сторінки..."
      return RedirectResponse("/chapter/" + chapter, status_code=303)


@app.post("/chapter/{chapter}/delete")
def delete(chapter):
      if is_working(chapter):
            return RedirectResponse("/chapter/" + chapter, status_code=303)
      for folder in ["input/", "data/", "output/"]:
            shutil.rmtree(folder + chapter, ignore_errors=True)
      for end in [" (UA).pdf", " (original).pdf", ".zip"]:
            if os.path.exists("exports/" + chapter + end):
                  os.remove("exports/" + chapter + end)
      status.pop(chapter, None)
      return RedirectResponse("/", status_code=303)


@app.get("/chapter/{chapter}", response_class=HTMLResponse)
def chapter_page(chapter):
      info = read_info(chapter)
      text = status.get(chapter, "")
      working = is_working(chapter)

      translated = 0
      if os.path.exists("output/" + chapter):
            translated = len(os.listdir("output/" + chapter))

      html = style
      if working:
            html += '<meta http-equiv="refresh" content="3">'
      html += '<a href="/">← на головну</a>'
      html += '<h1>' + escape(info["title"]) + ', розділ ' + escape(str(info["chapter"])) + '</h1>'
      html += '<p><a href="https://mangadex.org/chapter/' + chapter + '" target="_blank">Відкрити розділ на MangaDex ↗</a></p>'
      html += '<p class="hint">⚠️ Файли на сервері зберігаються тимчасово і видаляються після перезапуску. Завантажте PDF одразу після перекладу.</p>'
      if text != "":
            html += '<p class="status">' + escape(text) + '</p>'

      if working and chapter in progress:
            done, total = progress[chapter]
            percent = int(done * 100 / total)
            html += '<div class="bar"><div style="width:' + str(percent) + '%"></div></div>'
            html += '<p class="hint">' + str(percent) + '%. Одна сторінка перекладається приблизно 20–40 секунд. '
            html += 'Можна піти на головну або закрити вкладку: переклад продовжиться, а результат з\'явиться тут.</p>'

      if working:
            html += '<form method="post" action="/chapter/' + chapter + '/stop"><button class="red" type="submit">Зупинити</button></form>'
      else:
            html += '<form style="display:inline" method="post" action="/chapter/' + chapter + '/translate">'
            html += '<input type="hidden" name="lang" value="' + escape(info["language"] if info["language"] in config.LANGUAGES else "en") + '">'
            if translated == 0:
                  html += '<button type="submit">Перекласти українською</button></form> '
            else:
                  html += '<button type="submit">Перекласти / продовжити переклад</button></form> '
            html += '<a class="button gray" href="/chapter/' + chapter + '/pdf_original">PDF оригіналу</a> '
            if translated > 0:
                  html += '<a class="button" href="/chapter/' + chapter + '/pdf">PDF українською</a> '
                  html += '<a class="button gray" href="/chapter/' + chapter + '/zip">ZIP (JPG)</a> '
            html += '<form style="display:inline" method="post" action="/chapter/' + chapter + '/delete" onsubmit="return confirm(\'Видалити цей розділ?\')">'
            html += '<button class="red" type="submit">Видалити розділ</button></form>'
            html += '<form method="post" action="/chapter/' + chapter + '/rename" style="margin-top:15px">'
            html += 'Назва: <input type="text" name="title" style="width:400px" value="' + escape(info["title"]) + '"> '
            html += 'Розділ: <input type="text" name="number" style="width:60px" value="' + escape(str(info["chapter"])) + '"> '
            html += '<button class="outline" type="submit">Зберегти назву</button></form>'
            if translated > 0:
                  html += '<p class="hint">Клацніть на перекладену сторінку, щоб виправити текст.</p>'

      html += '<div class="pages">'
      folder = "input/" + chapter
      if os.path.exists(folder):
            stamp = str(time.time())
            for page in sorted(os.listdir(folder)):
                  name = page.split(".")[0]
                  if os.path.exists("output/" + chapter + "/" + name + ".jpg"):
                        html += '<a href="/chapter/' + chapter + '/page/' + name + '"><img src="/output/' + chapter + '/' + name + '.jpg?' + stamp + '"><br>' + name + ' ✏️ редагувати</a>'
                  else:
                        html += '<a href="/input/' + chapter + '/' + page + '" target="_blank"><img src="/input/' + chapter + '/' + page + '"><br>' + name + ' (оригінал)</a>'
      html += '</div>'
      return html


@app.get("/chapter/{chapter}/page/{name}", response_class=HTMLResponse)
def page(chapter, name):
      with open("data/" + chapter + "/" + name + ".json", "r", encoding="utf-8") as file:
            bubbles = json.load(file)

      image = find_image(chapter, name)
      stamp = str(time.time())

      html = style + '<a href="/chapter/' + chapter + '">← до розділу</a> <h2>' + name + '</h2>'
      html += '<div style="display:flex; gap:20px">'
      html += '<div><p>Оригінал</p><img src="/' + image + '" width="550"></div>'
      html += '<div><p>Переклад</p><img src="/output/' + chapter + '/' + name + '.jpg?' + stamp + '" width="550"></div>'
      html += '</div>'

      html += '<form method="post">'
      for i in range(len(bubbles)):
            uk = bubbles[i].get("uk", "")
            html += '<p><b>' + escape(bubbles[i]["src"]) + '</b><br>'
            html += '<textarea name="uk_' + str(i) + '" rows="2" cols="80">' + escape(uk) + '</textarea></p>'
      html += '<button type="submit">Перемалювати</button></form>'
      return html


@app.post("/chapter/{chapter}/page/{name}")
async def save_page(chapter, name, request: Request):
      form = await request.form()
      json_path = "data/" + chapter + "/" + name + ".json"

      with open(json_path, "r", encoding="utf-8") as file:
            bubbles = json.load(file)

      for i in range(len(bubbles)):
            bubbles[i]["uk"] = form["uk_" + str(i)]

      with open(json_path, "w", encoding="utf-8") as file:
            json.dump(bubbles, file, ensure_ascii=False, indent=2)

      render_page(find_image(chapter, name), json_path, "output/" + chapter + "/" + name + ".jpg")
      return RedirectResponse("/chapter/" + chapter + "/page/" + name, status_code=303)


def make_pdf(chapter, translated):
      images = []
      for page in sorted(os.listdir("input/" + chapter)):
            name = page.split(".")[0]
            path = "input/" + chapter + "/" + page
            if translated and os.path.exists("output/" + chapter + "/" + name + ".jpg"):
                  path = "output/" + chapter + "/" + name + ".jpg"
            images.append(Image.open(path).convert("RGB"))
      end = " (UA).pdf" if translated else " (original).pdf"
      path = "exports/" + chapter + end
      images[0].save(path, save_all=True, append_images=images[1:])
      return FileResponse(path, filename=file_name(chapter) + end)


@app.get("/chapter/{chapter}/pdf")
def pdf(chapter):
      if not os.path.exists("output/" + chapter) or len(os.listdir("output/" + chapter)) == 0:
            return RedirectResponse("/", status_code=303)
      return make_pdf(chapter, True)


@app.get("/chapter/{chapter}/pdf_original")
def pdf_original(chapter):
      if not os.path.exists("input/" + chapter):
            return RedirectResponse("/", status_code=303)
      return make_pdf(chapter, False)


@app.get("/chapter/{chapter}/zip")
def zip_file(chapter):
      if not os.path.exists("output/" + chapter):
            return RedirectResponse("/chapter/" + chapter, status_code=303)
      path = shutil.make_archive("exports/" + chapter, "zip", "output/" + chapter)
      return FileResponse(path, filename=file_name(chapter) + ".zip")
