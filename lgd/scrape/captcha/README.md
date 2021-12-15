`python collect.py` - collect captcha images from lgd website

`python create_testset.py` - to manually populate the `truth.json` file with captcha truth values

`python check.py` - to test out the captcha breaking code for accuracy

'python data_helper.py download` - to pull captcha test data and tesseract models from GCS

'python data_helper.py upload` - to push captcha test data and tesseract models from GCS, currently tied to my google account and my buckets.

