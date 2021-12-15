import sys
import glob
import mimetypes
import logging

from pathlib import Path
from google.cloud import storage
from google.api_core.exceptions import NotFound

logger = logging.getLogger(__name__)

bucket_map = {
    'data': 'lgd_captcha_samples',
    'models': 'lgd_captcha_tesseract_models'
}

def download_files(bucket_name, dirname, client=None):
    logger.info(f'downloading files from  {bucket_name} into {dirname}')
    if client is None:
        client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blobs = list(client.list_blobs(bucket))
    for blob in blobs:
        filename = blob.name
        path = Path(f'{dirname}{filename}')
        if path.exists():
            continue
        directory = path.parent
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f'downloading file {filename}')
        blob.download_to_filename(str(path))


def create_bucket(bucket_name, client=None, make_public=True):
    if client is None:
        client = storage.Client()

    try:
        bucket = client.get_bucket(bucket_name)
    except NotFound:
        logger.info(f'creating bucket {bucket_name}')
        bucket = client.create_bucket(bucket_name)
        if make_public:
            bucket.make_public(future=True)
    return bucket


def upload_file(bucket_name, dir_prefix, filename, client=None):
    blob_name = filename.replace(dir_prefix, '')
    logger.info(f'uploading {filename} into {bucket_name} as {blob_name}')
    if client is None:
        client = storage.Client()

    bucket = create_bucket(bucket_name, client)
    blob = bucket.blob(blob_name)
    if blob.exists():
        return blob
    
    blob.upload_from_filename(filename=filename)
    return blob


def upload_files(bucket_name, folder, client=None):
    logger.info(f'uploading files from {folder} into {bucket_name}')
    if client is None:
        client = storage.Client()

    create_bucket(bucket_name, client, True)
    filenames = []
    for filename in glob.iglob('{}/**/*'.format(folder), recursive=True):
        if Path(filename).is_dir():
            continue
        filenames.append(filename)

    for filename in filenames:
        upload_file(bucket_name, folder, filename, client)



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    usage = 'Usage: {} [upload|download]'.format(Path(sys.argv[0]).name)
    if len(sys.argv) < 2:
        logging.error('not enough arguments\n{}'.format(usage))
        exit()

    op = sys.argv[1]
    if op == 'upload':
        client = storage.Client()
        for dirname, bucket_name in bucket_map.items():
            upload_files(bucket_name, dirname, client)
        exit()

    if op == 'download':
        client = storage.Client.create_anonymous_client()
        for dirname, bucket_name in bucket_map.items():
            download_files(bucket_name, dirname, client)
        exit()

    logging.error(usage)
    

