#!/bin/bash

set -ex

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

date_str=$(date +%s)
instance_name="proxy-instance-$date_str"
project="lgd-data"
zone="asia-south1-a" 

gcloud compute instances create $instance_name\
    --project=$project \
    --zone=$zone\
    --machine-type=e2-micro \
    --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
    --no-restart-on-failure \
    --maintenance-policy=TERMINATE \
    --provisioning-model=SPOT \
    --instance-termination-action=DELETE \
    --max-run-duration=86400s \
    --tags=http-server \
    --create-disk=auto-delete=yes,boot=yes,device-name=$instance_name,image=projects/ubuntu-os-cloud/global/images/ubuntu-2004-focal-v20240731,mode=rw,size=10,type=pd-balanced \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=goog-ec-src=vm_add-gcloud \
    --reservation-affinity=any \
    --metadata-from-file startup-script=${SCRIPT_DIR}/startup.sh

echo "instance_name=$instance_name" > info.sh
echo "project=$project" >> info.sh
echo "zone=$zone" >> info.sh


# maybe wait till you get ip address
ip_address=$(gcloud compute instances describe $instance_name --project $project --zone $zone --format='json' | jq -r '.networkInterfaces[0].accessConfigs[0].natIP')
echo $ip_address > ip_address.txt

if [[ $ip_address == "" ]]; then
  exit 1
fi

counter=0
maxRetry=50
while true; do
  if (( $counter == $maxRetry )) ; then
    echo "Reach the retry upper limit $counter"
    exit 1
  fi
  if nc -z $ip_address 80; then
    echo "The machine is UP !!!"
    exit 0
  else
    echo "sleeping to check again $counter"
    counter=$((counter + 1))
    sleep 5
  fi
done
