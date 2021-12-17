import glob
import logging

from pathlib import Path
from google.cloud import storage
from google.api_core.exceptions import NotFound

logger = logging.getLogger(__name__)

def create_bucket(bucket_name, client=None, make_public=True):
    if client is None:
        client = storage.Client()

    try:
        bucket = client.get_bucket(bucket_name)
    except NotFound:
        logger.info(f'creating bucket {bucket_name}')
        bucket = client.create_bucket(bucket_name, location='ASIA-SOUTH1')
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


def upload_folder(bucket_name, folder, client=None):
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


def download_folder(bucket_name, dirname, client=None):
    logger.info(f'downloading files from  {bucket_name} into {dirname}')
    if client is None:
        client = storage.Client.create_anonymous_client()
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


