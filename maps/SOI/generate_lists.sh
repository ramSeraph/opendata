#!/bin/bash

gsutil ls -l gs://soi_data/raw/ | grep pdf | tr -s " " | cut -d" " -f2,4 | sed 's,gs://soi_data/raw/,,g' | sed 's,\.pdf,,g' > listing_pdfs.txt
gsutil ls -l gs://soi_data/export/gtiffs/ | tr -s " " | cut -d" " -f2,4 | sed 's,gs://soi_data/export/gtiffs/,,g' | sed 's,\.tif,,g' > listing_gtiffs.txt

gsutil -m cp listing_pdfs.txt gs://soi_data/listing_pdfs.txt
gsutil -m cp listing_gtiffs.txt gs://soi_data/listing_gtiffs.txt
