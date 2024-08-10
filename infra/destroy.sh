#!/bin/bash

source info.sh

gcloud compute instances stop $instance_name \
    --project=$project \
    --zone=$zone

gcloud compute instances delete $instance_name \
    --project=$project \
    --zone=$zone

