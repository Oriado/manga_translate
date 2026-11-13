from PIL import Image, ImageDraw, ImageFont
import os
import json
import config


def split_lines(draw, text, font, max_width):
      lines = []
      for part in text.splitlines():
            words = part.split()
            line = ""
            for word in words:
                  test = word if line == "" else line + " " + word
                  if draw.textlength(test, font=font) <= max_width:
                        line = test
                  else:
                        if line != "":
                              lines.append(line)
                        line = word
            if line != "":
                  lines.append(line)
      return lines


def fit_text(draw, text, width, height):
      size = 60
      while size > 10:
            font = ImageFont.truetype(config.FONT_PATH, size)
            lines = split_lines(draw, text, font, width)
            line_height = int(size * 1.2)
            if len(lines) == 0:
                  return font, lines, line_height
            widest = max(draw.textlength(line, font=font) for line in lines)
            if widest <= width and len(lines) * line_height <= height:
                  return font, lines, line_height
            size = size - 2
      font = ImageFont.truetype(config.FONT_PATH, 10)
      return font, split_lines(draw, text, font, width), 12


def render_page(image_path, json_path, output_path):
      image = Image.open(image_path)
      image = image.convert("RGB")
      draw = ImageDraw.Draw(image)

      with open(json_path, "r", encoding="utf-8") as file:
            bubbles = json.load(file)

      for bubble in bubbles:
            if "uk" not in bubble:
                  continue
            x1, y1, x2, y2 = bubble["box"]
            draw.rectangle([x1 - 5, y1 - 5, x2 + 5, y2 + 5], fill="white")

      for bubble in bubbles:
            if "uk" not in bubble:
                  continue
            x1, y1, x2, y2 = bubble["box"]
            width = x2 - x1
            height = y2 - y1
            font, lines, line_height = fit_text(draw, bubble["uk"], width, height)

            y = y1 + (height - len(lines) * line_height) // 2
            for line in lines:
                  line_width = draw.textlength(line, font=font)
                  x = x1 + (width - line_width) // 2
                  draw.text((x, y), line, font=font, fill="black")
                  y = y + line_height

      os.makedirs(os.path.dirname(output_path), exist_ok=True)
      image.save(output_path)


if __name__ == "__main__":
      import sys
      render_page(sys.argv[1], sys.argv[2], sys.argv[3])
