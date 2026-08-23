from pathlib import Path

from PIL import Image


ROOT = Path('/Users/phucit/Desktop/Work/Apps/Flutter/Projects/fake_voice_detector/docs/overleaf/springer_progress_report/figures')


def optimize_png(path: Path, colors: int) -> None:
    img = Image.open(path).convert('RGBA')
    alpha = img.getchannel('A')
    rgb = Image.new('RGB', img.size, 'white')
    rgb.paste(img, mask=alpha)
    pal = rgb.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    pal.save(path, format='PNG', optimize=True, compress_level=9)


if __name__ == '__main__':
    # Heavier charts benefit the most from palette reduction.
    chart_colors = {
        'image1_clean.png': 64,
        'image9_clean.png': 64,
        'image10_clean.png': 96,
        'image11_clean.png': 128,
        'image12_clean.png': 128,
    }
    screenshot_colors = {
        'image3.png': 192,
        'image4.png': 192,
        'image5.png': 192,
        'image6.png': 192,
        'image7.png': 192,
        'image8.png': 192,
    }

    for name, colors in {**chart_colors, **screenshot_colors}.items():
        optimize_png(ROOT / name, colors)
        print(f'optimized {name} with {colors} colors')
