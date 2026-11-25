import requests

API = "https://api.mangadex.org"


def get_title(attributes):
      titles = attributes["title"]
      if "en" in titles:
            return titles["en"]
      return list(titles.values())[0]


def get_cover(manga):
      for item in manga["relationships"]:
            if item["type"] == "cover_art" and "attributes" in item:
                  return item["attributes"]["fileName"]
      return None


def search_manga(text, adult=False):
      ratings = ["safe", "suggestive"]
      if adult:
            ratings = ["safe", "suggestive", "erotica", "pornographic"]

      params = {
            "title": text,
            "limit": 24,
            "includes[]": "cover_art",
            "contentRating[]": ratings,
            "order[relevance]": "desc",
      }
      response = requests.get(API + "/manga", params=params)
      data = response.json()

      results = []
      for manga in data["data"]:
            results.append({
                  "id": manga["id"],
                  "title": get_title(manga["attributes"]),
                  "cover": get_cover(manga),
                  "languages": manga["attributes"]["availableTranslatedLanguages"],
            })
      return results


def get_manga(manga_id):
      response = requests.get(API + "/manga/" + manga_id, params={"includes[]": "cover_art"})
      manga = response.json()["data"]
      description = manga["attributes"]["description"]
      return {
            "id": manga["id"],
            "title": get_title(manga["attributes"]),
            "cover": get_cover(manga),
            "description": description.get("en", ""),
            "rating": manga["attributes"]["contentRating"],
      }


def get_chapters(manga_id, lang, offset=0):
      params = {
            "translatedLanguage[]": lang,
            "order[chapter]": "asc",
            "limit": 100,
            "offset": offset,
            "includeExternalUrl": 0,
            "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
      }
      response = requests.get(API + "/manga/" + manga_id + "/feed", params=params)
      data = response.json()

      chapters = []
      for chapter in data["data"]:
            attributes = chapter["attributes"]
            if attributes["pages"] == 0:
                  continue
            chapters.append({
                  "id": chapter["id"],
                  "number": attributes["chapter"],
                  "title": attributes["title"],
                  "pages": attributes["pages"],
            })
      return chapters, data["total"]


def get_cover_image(manga_id, file_name):
      url = "https://uploads.mangadex.org/covers/" + manga_id + "/" + file_name + ".256.jpg"
      return requests.get(url).content
