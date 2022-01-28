import sys
import logging

from pathlib import Path
from google.cloud import storage

sys.path.append('..')
from gcs import download_folder, upload_folder

bucket_map = {
    'data': 'lgd_captcha_samples',
    'models': 'lgd_captcha_tesseract_models'
}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    usage = 'Usage: {} [upload|download]'.format(Path(sys.argv[0]).name)
    if len(sys.argv) < 2:
        logging.error('not enough arguments\n{}'.format(usage))
        exit()

    op = sys.argv[1]
    dirnames_to_pick = set(bucket_map.keys())

    if len(sys.argv) > 2:
        dirnames_to_pick = set([sys.argv[2]])

    if op == 'upload':
        client = storage.Client()
        for dirname, bucket_name in bucket_map.items():
            if dirname in dirnames_to_pick:
                upload_folder(bucket_name, dirname, client)
        exit()

    if op == 'download':
        client = storage.Client.create_anonymous_client()
        for dirname, bucket_name in bucket_map.items():
            if dirname in dirnames_to_pick:
                download_folder(bucket_name, dirname, client)
        exit()

    logging.error(usage)
