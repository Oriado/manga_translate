import os
import json
import time
from PIL import Image
import config
from translate import ask_gemini

readers = {}


def get_reader(lang):
      import torch
      import easyocr
      if lang not in readers:
            readers[lang] = easyocr.Reader(config.LANGUAGES[lang]["ocr"], gpu=torch.cuda.is_available())
      return readers[lang]


def detect_text(image_path, lang="en"):
      if config.DETECTOR == "gemini":
            return detect_gemini(image_path, lang)
      return detect_easyocr(image_path, lang)


def detect_gemini(image_path, lang):
      prompt = "Це сторінка манги. Знайди весь текст " + config.LANGUAGES[lang]["name"] + " мовою: репліки в бульбашках, підписи, написи.\n"
      prompt += "Японські ієрогліфи і намальовані японською звуки ігноруй.\n"
      prompt += "Одна бульбашка = один елемент. box_2d [ymin, xmin, ymax, xmax] від 0 до 1000 має охоплювати ВСІ рядки тексту цієї бульбашки повністю, з невеликим запасом.\n"
      prompt += "text = оригінальний текст, uk = переклад живою природною українською з емоцією персонажа. Звуки перекладай українськими звуками за змістом картинки.\n"
      prompt += "Поверни тільки JSON масив об'єктів з полями box_2d, text, uk."

      answer = ask_gemini(prompt, image_path)
      tries = 1
      while answer is None and tries < 3:
            time.sleep(10)
            answer = ask_gemini(prompt, image_path)
            tries = tries + 1
      if answer is None:
            raise Exception("Gemini не відповів")

      width, height = Image.open(image_path).size

      bubbles = []
      for item in answer:
            ymin, xmin, ymax, xmax = item["box_2d"]
            box = [int(xmin * width / 1000), int(ymin * height / 1000), int(xmax * width / 1000), int(ymax * height / 1000)]
            bubbles.append({"box": box, "src": item["text"], "uk": item["uk"]})
      return bubbles


def detect_easyocr(image_path, lang):
      results = get_reader(lang).readtext(image_path, paragraph=True)

      bubbles = []
      for result in results:
            points = result[0]
            text = result[1]

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            box = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]

            bubbles.append({"box": box, "src": text})

      return bubbles


def save_json(bubbles, json_path):
      folder = os.path.dirname(json_path)
      os.makedirs(folder, exist_ok=True)
      with open(json_path, "w", encoding="utf-8") as file:
            json.dump(bubbles, file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
      import sys
      bubbles = detect_text(sys.argv[1])
      for bubble in bubbles:
            print(bubble)
