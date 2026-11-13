import os
import json
import time
import shutil
from html import escape
from PIL import Image
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from download_chapter import get_chapter_id, get_chapter_details, download_chapter
from pipeline import process_page
from render import render_page
import config

os.makedirs("input", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("exports", exist_ok=True)

app = FastAPI()
app.mount("/input", StaticFiles(directory="input"), name="input")
app.mount("/output", StaticFiles(directory="output"), name="output")

status = {}
stop = set()

style = """
<style>
body { font-family: sans-serif; max-width: 1300px; margin: 30px auto; padding: 0 20px; }
input[type=text] { width: 600px; padding: 10px; font-size: 16px; }
select { padding: 10px; font-size: 16px; }
button, .button { padding: 10px 18px; font-size: 16px; background: #222; color: white; border: none; border-radius: 6px; text-decoration: none; cursor: pointer; }
.red { background: #b00; }
.pages { display: flex; flex-wrap: wrap; gap: 12px; }
.pages a, .pages div { width: 180px; text-align: center; color: #222; text-decoration: none; font-size: 14px; }
.pages img { width: 180px; border: 1px solid #ccc; }
.hint { color: #555; }
.error { color: #b00; }
</style>
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
                  if chapter_id in stop:
                        status[chapter_id] = "Зупинено на сторінці " + str(i + 1) + ". Натисніть «Продовжити переклад», щоб продовжити."
                        return
                  status[chapter_id] = "Перекладаю сторінку " + str(i + 1) + " з " + str(len(pages))
                  if not process_page(chapter_id, pages[i], lang):
                        failed = failed + 1

            if failed > 0:
                  status[chapter_id] = "Готово, але " + str(failed) + " сторінок не перекладено (можливо, закінчився ліміт Gemini). Натисніть «Продовжити переклад» пізніше."
            else:
                  status[chapter_id] = "Готово"
      except Exception as error:
            status[chapter_id] = "Помилка: " + str(error)


@app.get("/", response_class=HTMLResponse)
def index(error: str = ""):
      html = style + "<h1>Manga Translator</h1>"
      html += "<p>Вставте посилання на розділ з MangaDex. Спочатку завантажаться сторінки, а перекладати можна буде кнопкою.</p>"
      html += '<form method="post" action="/start">'
      html += '<input type="text" name="link" placeholder="https://mangadex.org/chapter/..."> '
      html += '<button type="submit">Завантажити</button></form>'
      if error != "":
            html += '<p class="error">' + escape(error) + '</p>'
      html += '<p class="hint">Де взяти посилання: відкрийте mangadex.org, знайдіть мангу, відкрийте розділ і скопіюйте адресу з браузера.</p>'

      html += "<h2>Розділи</h2>"
      for chapter in sorted(os.listdir("input")):
            info = read_info(chapter)
            html += '<p><a href="/chapter/' + chapter + '">' + escape(info["title"]) + ', розділ ' + escape(str(info["chapter"])) + '</a> '
            html += escape(status.get(chapter, "")) + '</p>'
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
      for end in [".pdf", ".zip"]:
            if os.path.exists("exports/" + chapter + end):
                  os.remove("exports/" + chapter + end)
      status.pop(chapter, None)
      return RedirectResponse("/", status_code=303)


@app.get("/chapter/{chapter}", response_class=HTMLResponse)
def chapter_page(chapter):
      info = read_info(chapter)
      text = status.get(chapter, "")
      working = is_working(chapter)

      html = style
      if working:
            html += '<meta http-equiv="refresh" content="3">'
      html += '<a href="/">← на головну</a>'
      html += '<h1>' + escape(info["title"]) + ', розділ ' + escape(str(info["chapter"])) + '</h1>'
      html += '<p><b>' + escape(text) + '</b></p>'

      if working:
            html += '<form method="post" action="/chapter/' + chapter + '/stop"><button class="red" type="submit">Зупинити</button></form>'
      else:
            html += '<form style="display:inline" method="post" action="/chapter/' + chapter + '/translate">'
            html += '<select name="lang">'
            for code in config.LANGUAGES:
                  selected = " selected" if code == info["language"] else ""
                  html += '<option value="' + code + '"' + selected + '>З ' + config.LANGUAGES[code]["name"] + '</option>'
            html += '</select> '
            html += '<button type="submit">Перекласти / Продовжити переклад</button></form> '
            html += '<a class="button" href="/chapter/' + chapter + '/pdf">PDF</a> '
            html += '<a class="button" href="/chapter/' + chapter + '/zip">ZIP (JPG)</a> '
            html += '<form style="display:inline" method="post" action="/chapter/' + chapter + '/delete" onsubmit="return confirm(\'Видалити цей розділ?\')">'
            html += '<button class="red" type="submit">Видалити розділ</button></form>'
            html += '<form method="post" action="/chapter/' + chapter + '/rename" style="margin-top:15px">'
            html += 'Назва: <input type="text" name="title" style="width:400px" value="' + escape(info["title"]) + '"> '
            html += 'Розділ: <input type="text" name="number" style="width:60px" value="' + escape(str(info["chapter"])) + '"> '
            html += '<button type="submit">Зберегти назву</button></form>'
            html += '<p class="hint">Уже перекладені сторінки пропускаються. Клацніть на перекладену сторінку, щоб редагувати текст.</p>'

      html += '<div class="pages">'
      folder = "input/" + chapter
      if os.path.exists(folder):
            stamp = str(time.time())
            for page in sorted(os.listdir(folder)):
                  name = page.split(".")[0]
                  if os.path.exists("output/" + chapter + "/" + name + ".jpg"):
                        html += '<a href="/chapter/' + chapter + '/page/' + name + '"><img src="/output/' + chapter + '/' + name + '.jpg?' + stamp + '"><br>' + name + ' ✏️ редагувати</a>'
                  else:
                        html += '<div><img src="/input/' + chapter + '/' + page + '"><br>' + name + ' (не перекладено)</div>'
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


@app.get("/chapter/{chapter}/pdf")
def pdf(chapter):
      folder = "output/" + chapter
      if not os.path.exists(folder) or len(os.listdir(folder)) == 0:
            return RedirectResponse("/chapter/" + chapter, status_code=303)
      images = [Image.open(folder + "/" + page).convert("RGB") for page in sorted(os.listdir(folder))]
      path = "exports/" + chapter + ".pdf"
      images[0].save(path, save_all=True, append_images=images[1:])
      return FileResponse(path, filename=file_name(chapter) + ".pdf")


@app.get("/chapter/{chapter}/zip")
def zip_file(chapter):
      if not os.path.exists("output/" + chapter):
            return RedirectResponse("/chapter/" + chapter, status_code=303)
      path = shutil.make_archive("exports/" + chapter, "zip", "output/" + chapter)
      return FileResponse(path, filename=file_name(chapter) + ".zip")
