from PIL import Image, ImageDraw
import math
import os
import subprocess
import sys

def create_image(size):
    image = Image.new("RGBA", size, color=(30, 30, 30, 0))
    d = ImageDraw.Draw(image)

    d.polygon([
        (10, size[1] - 16),
        (size[0] - 10, size[1] - 16),
        (size[0] - 16, size[1] - 8),
        (16, size[1] - 8)
    ], fill="blue", outline="white")

    center = (size[0] // 2, size[1] - 16)

    page_angles = [-70, -50, -30, -15, 0, 15, 30, 50, 70]
    for angle in page_angles:
        endX = center[0] + int((size[0] // 2 - 8) * math.sin(math.radians(angle)))
        endY = center[1] - int((size[1] // 2) * math.cos(math.radians(angle)))
        d.line([center, (endX, endY)], fill="white", width=max(1, size[0] // 64))

    return image

def generate_icns():
    iconset_dir = "icon.iconset"
    os.makedirs(iconset_dir, exist_ok=True)

    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for size in sizes:
        img = create_image((size, size))
        img.save(f"{iconset_dir}/icon_{size}x{size}.png")
        if size != 1024:
            img2x = create_image((size * 2, size * 2))
            img2x.save(f"{iconset_dir}/icon_{size}x{size}@2x.png")

    if sys.platform == "darwin":
        subprocess.run(["iconutil", "-c", "icns", iconset_dir], check=True)
        print("✅ icon.icns generated successfully.")

if __name__ == "__main__":
    generate_icns()