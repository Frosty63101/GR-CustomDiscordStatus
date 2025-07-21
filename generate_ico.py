from PIL import Image, ImageDraw
import math

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

def save_ico():
    size = (256, 256)
    img = create_image(size)
    img.save("icon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

if __name__ == "__main__":
    save_ico()