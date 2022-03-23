import glob
import json
import shutil
from pathlib import Path
from PIL import Image
from imgcat import imgcat

truth_file = 'data/captcha/truth.json'
if not Path(truth_file).exists():
    with open(truth_file, 'w') as f:
        f.write('{}')

with open(truth_file, 'r') as f:
    truth_data = json.load(f)

filenames = glob.glob('data/captcha/imgs/*.jpeg')

for filename in filenames:
    if filename in truth_data:
        continue
    print(f'annotating {filename}')
    img = Image.open(filename)
    imgcat(img)
    inp = input('Enter Captcha Value:')
    val = inp.strip()
    truth_data[filename] = val

with open(f'{truth_file}.new', 'w') as f:
    json.dump(truth_data, f, indent = 2)

shutil.move(f'{truth_file}.new', truth_file)
