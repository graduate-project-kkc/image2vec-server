import random
import os
from PIL import Image

for size in range(1, 33):
    print(f"{size=} ({size<<7})")
    for idx in range(1, 6):
        chunks = size<<5
        width = chunks<<2
        height = chunks<<2
        img = Image.new("RGB", (width, height))
        for x in range(width>>2):
            for y in range(height>>2):
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                for i in range(4):
                    for j in range(4):
                        img.putpixel((i+(x<<2), j+(y<<2)), color)
        img.save(os.path.join(r"C:\Users\frien\Desktop\random_images", f"rand{chunks<<2}_{idx}.jpg"))
    for idx in range(1, 6):
        chunks = size<<5
        width = chunks<<2
        height = chunks<<1
        img = Image.new("RGB", (width, height))
        for x in range(width>>2):
            for y in range(height>>2):
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                for i in range(4):
                    for j in range(4):
                        img.putpixel((i+(x<<2), j+(y<<2)), color)
        img.save(os.path.join(r"C:\Users\frien\Desktop\random_images", f"rand{chunks<<2}half_{idx}.jpg"))

