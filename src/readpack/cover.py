import hashlib
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 600, 900

_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


def _font(size: int) -> ImageFont.ImageFont:
    for p in _FONTS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def _wrap(text: str, font: ImageFont.ImageFont, max_w: int) -> list[str]:
    words, lines, buf = text.split(), [], []
    for w in words:
        test = " ".join(buf + [w])
        bx = font.getbbox(test)
        if bx[2] - bx[0] > max_w and buf:
            lines.append(" ".join(buf))
            buf = [w]
        else:
            buf.append(w)
    if buf:
        lines.append(" ".join(buf))
    return lines


def generate_cover(title: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(int(hashlib.md5(title.encode()).hexdigest()[:8], 16))

    # Gradient background
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    c1 = (rng.randint(5, 25), rng.randint(5, 20), rng.randint(60, 110))
    c2 = (rng.randint(30, 70), rng.randint(5, 45), rng.randint(100, 170))
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=tuple(int(c1[i] + t * (c2[i] - c1[i])) for i in range(3)))

    # Bokeh orbs
    orb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(orb)
    for _ in range(22):
        x, y = rng.randint(-100, W + 100), rng.randint(-100, H + 100)
        r = rng.randint(25, 150)
        od.ellipse(
            [x - r, y - r, x + r, y + r],
            fill=(rng.randint(80, 255), rng.randint(80, 255), rng.randint(180, 255), rng.randint(8, 48)),
        )
    img = Image.alpha_composite(img.convert("RGBA"), orb.filter(ImageFilter.GaussianBlur(28))).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Title (title-cased, never slug-form)
    title_text = title.title()
    font_lg = _font(58)
    font_sm = _font(22)
    lines = _wrap(title_text, font_lg, W - 100)
    heights = [font_lg.getbbox(l)[3] - font_lg.getbbox(l)[1] for l in lines]
    total_h = sum(heights) + 14 * (len(lines) - 1)
    y_cur = (H - total_h) // 2 - 60

    for i, line in enumerate(lines):
        bx = font_lg.getbbox(line)
        x = (W - (bx[2] - bx[0])) // 2
        draw.text((x + 3, y_cur + 3), line, font=font_lg, fill=(0, 0, 20))
        draw.text((x, y_cur), line, font=font_lg, fill=(240, 242, 255))
        y_cur += heights[i] + 14

    # Accent line below title
    mid_y = (H - total_h) // 2 - 60 + total_h + 24
    draw.line([(80, mid_y), (W - 80, mid_y)], fill=(180, 185, 230), width=1)

    # Branding
    bx = font_sm.getbbox("readpack")
    draw.text(((W - (bx[2] - bx[0])) // 2, H - 70), "readpack", font=font_sm, fill=(155, 160, 195))

    cover_path = out_dir / "cover.png"
    img.save(cover_path)
    return cover_path
