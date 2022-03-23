#!/bin/bash

cd data
gsutil -m rsync -r raw gs://soi_data/raw/
gsutil -m acl ch -r -u AllUsers:R gs://soi_data/raw/
