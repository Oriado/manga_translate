import os
import sys
import requests


def get_chapter_id(text):
      text = text.strip().rstrip("/")
      parts = text.split("/")
      for i in range(len(parts)):
            if parts[i] == "chapter" and i + 1 < len(parts):
                  return parts[i + 1]
      if len(text) == 36 and text.count("-") == 4:
            return text
      return None


def get_chapter_info(chapter_id):
      response = requests.get("https://api.mangadex.org/chapter/" + chapter_id)
      data = response.json()
      take_pages = data["data"]["attributes"]["pages"]
      return take_pages


def get_chapter_language(chapter_id):
      return get_chapter_details(chapter_id)["language"]


def get_chapter_details(chapter_id):
      response = requests.get("https://api.mangadex.org/chapter/" + chapter_id + "?includes[]=manga")
      data = response.json()
      attributes = data["data"]["attributes"]

      title = "?"
      rating = "?"
      for item in data["data"]["relationships"]:
            if item["type"] == "manga":
                  titles = item["attributes"]["title"]
                  title = list(titles.values())[0]
                  rating = item["attributes"]["contentRating"]

      language = attributes["translatedLanguage"]
      if language.startswith("zh"):
            language = "zh"

      return {
            "title": title,
            "chapter": attributes["chapter"],
            "language": language,
            "rating": rating,
      }


def download_chapter(chapter_id):
      response = requests.get("https://api.mangadex.org/at-home/server/" + chapter_id)
      data = response.json()
      base_adres_server = data["baseUrl"]  #url адреса певної картинки 3 пунки
      take_value = data["chapter"]["hash"]
      all_pages = data["chapter"]["data"]

      folder = "input/" + chapter_id
      os.makedirs(folder, exist_ok=True)

      number = 1
      for page_filename in all_pages:
            konkat = base_adres_server + "/" + "data" + "/" + take_value + "/" + page_filename
            extension = page_filename.split(".")[-1]
            path = folder + "/page_" + str(number).zfill(2) + "." + extension
            if not os.path.exists(path):
                  picture = requests.get(konkat)
                  with open(path, "wb") as file:
                        file.write(picture.content)
            print(path)
            number = number + 1

      return folder


if __name__ == "__main__":
      chapter_id = get_chapter_id(sys.argv[1])
      print("Сторінок:", get_chapter_info(chapter_id))
      download_chapter(chapter_id)
