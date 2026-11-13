import os
import json
import torch
import easyocr
import config

readers = {}


def get_reader(lang):
      if lang not in readers:
            readers[lang] = easyocr.Reader(config.LANGUAGES[lang]["ocr"], gpu=torch.cuda.is_available())
      return readers[lang]


def detect_text(image_path, lang="en"):
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
