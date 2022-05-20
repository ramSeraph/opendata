import glob
import time
import subprocess
from multiprocessing import Pool
from pathlib import Path

def run_external(cmd):
    print(f'running cmd - {cmd}')
    start = time.time()
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end = time.time()
    print(f'command took {end - start} secs to run')
    if res.returncode != 0:
        print(f'STDOUT: {res.stdout}')
        print(f'STDERR: {res.stderr}')
        raise Exception(f'command {cmd} failed')


def translate_file(filename):
    sheet_no = Path(filename).parent.name
    out_filename = f'export/gtiffs/{sheet_no}.tif'
    if Path(out_filename).exists():
        return out_filename
    creation_opts = '-co TILED=YES -co COMPRESS=JPEG -co JPEG_QUALITY=10 -co PHOTOMETRIC=YCBCR' 
    mask_options = '--config GDAL_TIFF_INTERNAL_MASK YES  -b 1 -b 2 -b 3 -mask 4'
    perf_options = '--config GDAL_CACHEMAX 512'
    cmd = f'gdal_translate {mask_options} {creation_opts} {filename} {out_filename}'
    run_external(cmd)
    return out_filename


if __name__ == '__main__':
    filenames = glob.glob('data/inter/*/final.tif')
    with open('all_filenames.txt', 'w') as f:
        f.write('\n'.join(filenames))
    nb_processes = 8
    done = 0
    total = len(filenames)
    chunksize = max(1, min(128, total // nb_processes))
    chunksize = 10
    with Pool(processes=nb_processes) as pool:
        for out_filename in pool.imap_unordered(translate_file, filenames, chunksize=chunksize):
            done += 1
            print(f'done with file {out_filename} - {done}/{total}')


