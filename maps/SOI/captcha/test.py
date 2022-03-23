import json

from captcha.auto import guess

with open('data/captcha/truth.json') as f:
    truth_data = json.load(f)

success = 0
total_count = len(truth_data)
curr_count = 0
for filename, value in truth_data.items():
    guessed = guess(filename, 'data/captcha/models/')
    curr_count += 1
    outcome = 'FAILED'
    if guessed == value:
        outcome = 'SUCCESS'
        success += 1
    print(f'{curr_count:2}/{total_count:2} {guessed:6} {outcome:7} {success:2}/{curr_count}')

