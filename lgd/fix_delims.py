import csv
import glob
import zipfile
import shutil
from pathlib import Path 
from google.cloud import storage

# from bucket get archive list
# for each archive
#   download archive
#   unzip
#   for each file in archive
#      convert file delims
#   zip fixed files
#   upload fixed archive

# fix changes file as well

def convert_csv_delims(from_file, to_file):
    Path(to_file).parent.mkdir(parents=True, exist_ok=True)
    with open(from_file, 'r') as f:
        reader = csv.reader(f, delimiter=';')
        with open(to_file, 'w') as out_f:
            wr = csv.writer(out_f)
            for row in reader:
                wr.writerow(row)

bucket_name = 'lgd_data_archive'
client = storage.Client()
bucket = client.get_bucket(bucket_name)
blobs = list(client.list_blobs(bucket))
print('downloading files')
for blob in blobs:
    print(f'downloading {blob.name}')
    download_to = f'staging/download/{blob.name}'
    Path(download_to).parent.mkdir(parents=True, exist_ok=True)
    if Path(download_to).exists():
        continue
    print(f'downloading file {download_to}')
    blob.download_to_filename(download_to)

print('unzipping files')
unzipped_location_base = 'staging/unzipped'
for blob in blobs:
    print(f'unzipping {blob.name}')
    download_location = f'staging/download/{blob.name}'
    unzipped_location = f'{unzipped_location_base}/{blob.name}'.replace('.zip', '')

    zip_filename = f'staging/upload/{blob.name}'
    if Path(zip_filename).exists():
        continue

    Path(unzipped_location).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(download_location, 'r') as zip_ref:
        zip_ref.extractall(unzipped_location_base)
    filenames = glob.glob(f'{unzipped_location}/*')
    for filename in filenames:
        converted_file_name = filename.replace('unzipped', 'converted')
        print(f'converting {filename}')
        if Path(converted_file_name).exists():
            continue
        if filename.endswith('.csv'):
            convert_csv_delims(filename, converted_file_name)
        else:
            shutil.copyfile(filename, converted_file_name)
    Path(zip_filename).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_LZMA) as zip_obj:
        for filename in filenames:
            converted_file_name = filename.replace('unzipped', 'converted')
            path = Path(converted_file_name)
            date_str = path.parent.name
            arcname = '/{}/{}'.format(date_str, path.name)
            zip_obj.write(converted_file_name, arcname)

    date_str = Path(blob.name).stem
    unziiped_folder_name = f'staging/unzipped/{date_str}'
    converted_folder_name = f'staging/converted/{date_str}'
    shutil.rmtree(unziiped_folder_name)
    shutil.rmtree(converted_folder_name)

for blob in blobs:
    upload_from = f'staging/upload/{blob.name}'
    marker_file = upload_from + '.uploaded'
    print(f'uploading blob: {blob.name}')
    if Path(marker_file).exists():
        continue
    blob.upload_from_filename(filename=upload_from, timeout=600)
    with open(marker_file, 'w'):
        pass


print('dealing with changes files')


bucket_name = 'lgd_data_raw'
bucket = client.get_bucket(bucket_name)
blob = bucket.blob('changes/combined.csv')
changes_filename = 'staging/download/changes_combined.csv'
blob.download_to_filename(changes_filename)
changes_filename_out = 'staging/upload/changes_combined.csv'
convert_csv_delims(changes_filename, changes_filename_out)
blob.upload_from_filename(changes_filename_out, timeout=600)

