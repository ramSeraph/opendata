
from google.cloud import storage

client = storage.Client()
blobs = client.list_blobs('soi_data', prefix='raw/')
#blob_names = [ b.name for b in blobs ]
pdfs = {}
u_pdfs = {}
for blob in blobs:
    if blob.name.endswith('.pdf'):
        pdfs[blob.name] = blob
    if blob.name.endswith('.pdf.unavailable'):
        u_pdfs[blob.name] = blob

print(f'{u_pdfs.keys()=}')
#print(f'{pdfs.keys()=}')
to_delete = []
for b in u_pdfs.values():
    m_pdf = b.name.replace('.unavailable', '')
    print(m_pdf)
    if m_pdf in pdfs:
        to_delete.append(b)

to_del_names = [ b.name for b in to_delete ]
print(to_del_names)

