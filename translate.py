import os
import json
import base64
import time
import requests
from dotenv import load_dotenv
import config

load_dotenv()

last_error = None


def ask_gemini(prompt, image_path):
      global last_error
      last_error = None
      key = os.getenv("GEMINI_API_KEY")
      url = "https://generativelanguage.googleapis.com/v1beta/models/" + config.GEMINI_MODEL + ":generateContent"

      with open(image_path, "rb") as file:
            image = base64.b64encode(file.read()).decode("utf-8")

      mime = "image/png"
      if image_path.endswith(".jpg") or image_path.endswith(".jpeg"):
            mime = "image/jpeg"
      if image_path.endswith(".webp"):
            mime = "image/webp"

      body = {
            "contents": [{"parts": [
                  {"inline_data": {"mime_type": mime, "data": image}},
                  {"text": prompt}
            ]}],
            "generationConfig": {"responseMimeType": "application/json"}
      }

      try:
            response = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=120)
      except Exception as error:
            print(error)
            return None
      data = response.json()

      if "candidates" not in data:
            print(data)
            if "error" in data:
                  last_error = data["error"]["code"]
            return None

      answer = data["candidates"][0]["content"]["parts"][0]["text"]
      return json.loads(answer)


def translate_gemini(texts, image_path, lang):
      prompt = "Ти перекладач манги з " + config.LANGUAGES[lang]["name"] + " на українську.\n"
      prompt += "Нижче репліки з однієї сторінки, по порядку. Текст розпізнаний OCR, тому можуть бути помилки в словах, виправ їх за змістом.\n"
      prompt += "Дивись на картинку сторінки, щоб розуміти, що відбувається і хто говорить.\n"
      prompt += "Якщо одна репліка розбита на кілька частин, переклади так, щоб разом вони читались як одна фраза.\n"
      prompt += "Звуки перекладай українськими звуками за змістом картинки (поцілунок = Цмок, удар = Бах).\n"
      prompt += "Перекладай живою природною українською, як говорять персонажі, з емоцією.\n"
      prompt += "Поверни тільки JSON масив рядків, рівно " + str(len(texts)) + " елементів, у тому ж порядку. Кожна частина має свій елемент, нічого не склеюй.\n\n"
      prompt += json.dumps(texts, ensure_ascii=False)

      answer = ask_gemini(prompt, image_path)
      if answer is None:
            return []
      return answer


def translate_texts(texts, image_path, lang):
      if config.TRANSLATOR == "gemini":
            return translate_gemini(texts, image_path, lang)
      print("Немає такого перекладача:", config.TRANSLATOR)
      return []


def translate_page(json_path, image_path, lang="en"):
      with open(json_path, "r", encoding="utf-8") as file:
            bubbles = json.load(file)

      if len(bubbles) == 0:
            return

      if all("uk" in bubble for bubble in bubbles):
            return

      texts =[bubble["src"] for bubble in bubbles]
      translations = translate_texts(texts, image_path, lang)
      tries = 1
      while len(translations) != len(bubbles) and tries < 3 and last_error != 429:
            print("Пробую ще раз...")
            time.sleep(10)
            translations = translate_texts(texts, image_path, lang)
            tries = tries + 1

      if len(translations) != len(bubbles):
            print("Кількість перекладів не збігається:", len(translations), "замість", len(bubbles))
            return

      for i in range(len(bubbles)):
            bubbles[i]["uk"] = translations[i]

      with open(json_path, "w", encoding="utf-8") as file:
            json.dump(bubbles, file, ensure_ascii=False, indent=2)

      for bubble in bubbles:
            print(bubble["src"], "->", bubble["uk"])


if __name__ == "__main__":
      import sys
      translate_page(sys.argv[1], sys.argv[2])
