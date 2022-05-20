import glob
import io
from PIL import Image
from pathlib import Path

def webp_to_png(inp_buf):
    inp_f = io.BytesIO(inp_buf)
    img = Image.open(inp_f, formats=('WEBP',))
    with io.BytesIO() as f:
        img.save(f, format='PNG', params={'optimize': True})
        content = f.getvalue()
    return content


if __name__ == '__main__':
    #filename = 'export/tiles/15/22596/14157.webp'
    filenames = glob.glob('export/tiles/15/22596/*.webp')
    for filename in filenames:
        print(filename)
        out_filename = filename.replace('.webp', '.png').replace('tiles/', 'tiles_png/')
        out_file = Path(out_filename)
        if out_file.exists():
            continue
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'rb') as f:
            inp_buf = f.read()
        out_buf = webp_to_png(inp_buf)
        with open(out_filename, 'wb') as f:
            f.write(out_buf)
