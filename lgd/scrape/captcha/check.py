from pathlib import Path
import glob
import json
from lib import guess, print_buf, reset_buf


with open('data/truth.json') as f:
    truth = json.load(f)

success = 0
success_seg = 0
total = len(truth)
files = glob.glob('data/test/*.png')
count = 0
#files = [files[26]]
split_files = [
    'data/test/375.png',
    'data/test/74.png',
    'data/test/163.png',
    'data/test/604.png',
    'data/test/566.png',
]
#files = split_files

for full_filename in files:
    filename = full_filename.replace('data/','')
    if filename not in truth:
        continue

    models_path = str(Path(__file__).parent.joinpath('models'))
    prediction = guess(full_filename, models_path)
    #matched = False
    #if truth[filename] == captcha_code:
    #    matched = True
    #    success += 1

    matched_seg = False
    if truth[filename] == prediction:
        matched_seg = True
        success_seg += 1
        reset_buf()
    else:
        print_buf()
        

    count += 1

    #print_l('captcha code is: {}/{}/{} for file: {}, match: {}/{} [{}/{}/{}]'.format(
    print('captcha code is: {}/{} for file: {}, match: {} [{}/{}]'.format(
        prediction,
        #captcha_code,
        truth[filename], filename,
        'SUCCESS' if matched_seg else 'FAILED',
        #'SUCCESS' if matched else 'FAILED',
        success_seg,
        #success,
        count))

print('final report: TOTAL: {}, SUCCESS: {}'.format(total, success_seg))
#print('final report({}): TOTAL: {}, SUCCESS: {}'.format(config, total, success))
