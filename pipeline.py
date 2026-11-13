import os
import sys
import json
import time
from detect_ocr import detect_text, save_json
from translate import translate_page
from render import render_page
from download_chapter import get_chapter_id, get_chapter_language, download_chapter
import config


def is_translated(json_path):
      if not os.path.exists(json_path):
            return False
      with open(json_path, "r", encoding="utf-8") as file:
            bubbles = json.load(file)
      for bubble in bubbles:
            if "uk" not in bubble:
                  return False
      return True


def process_page(chapter, page, lang="en"):
      name = page.split(".")[0]
      image_path = "input/" + chapter + "/" + page
      json_path = "data/" + chapter + "/" + name + ".json"
      output_path = "output/" + chapter + "/" + name + ".jpg"

      if is_translated(json_path) and os.path.exists(output_path):
            print(page, "вже є, пропускаю")
            return True

      if not os.path.exists(json_path):
            bubbles = detect_text(image_path, lang)
            save_json(bubbles, json_path)
            print(page, "знайдено текстів:", len(bubbles))

      translate_page(json_path, image_path, lang)
      render_page(image_path, json_path, output_path)
      time.sleep(5)
      return is_translated(json_path)


def run_chapter(chapter, lang="en"):
      pages = sorted(os.listdir("input/" + chapter))
      for page in pages:
            process_page(chapter, page, lang)
      print("Готово:", "output/" + chapter)


if __name__ == "__main__":
      chapter = get_chapter_id(sys.argv[1])
      lang = get_chapter_language(chapter)
      if lang not in config.LANGUAGES:
            print("Мова розділу не підтримується:", lang)
            sys.exit()
      print("Мова:", lang)
      download_chapter(chapter)
      run_chapter(chapter, lang)
