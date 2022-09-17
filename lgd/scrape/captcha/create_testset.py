import glob
import json

from pathlib import Path

from PIL import Image, ImageOps

from lib import print_image

truth_file = Path('data/truth.json')
out = {}
if truth_file.exists(truth_file):
    with open(truth_file) as f:
        out = json.load(f)

files = glob.glob('data/test/*.png')
for filename in files:
    filename_e = filename.replace('data/', '')
    if filename_e in out:
        print('ignoring processed file: {}'.format(filename))
        continue
    image = Image.open(filename)
    image = image.convert('RGB')
    image = image.convert('L')
    image = ImageOps.invert(image)

    print_image(image)
    try:
        captcha_code = input("Enter captcha : ")
    except KeyboardInterrupt:
        break
    out[filename_e] = captcha_code

with open(truth_file, 'w') as f:
    json.dump(out, f, indent=4)
