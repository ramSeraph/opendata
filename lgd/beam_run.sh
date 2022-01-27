#/bin/bash
if [[ $BUILD == "1" ]]; then
	docker build --platform linux/amd64 . -t asia.gcr.io/lgd-data/beam-lgd
	docker push asia.gcr.io/lgd-data/beam-lgd
fi
docker run --platform linux/amd64 --rm -i -v "$(pwd)"/lgd-owner.json:/lgd-owner.json -e GOOGLE_APPLICATION_CREDENTIALS=/lgd-owner.json --entrypoint /usr/local/bin/python -t asia.gcr.io/lgd-data/beam-lgd -m scrape -m BEAM_RUN -l DEBUG -R 300 --runner DataflowRunner --project lgd-data --temp_location gs://lgd_dataflow/temp --region asia-south1 --experiment use_runner_v2 --sdk_container_image asia.gcr.io/lgd-data/beam-lgd --sdk_location container --enable-gcs --captcha-model-dir /lgd_models --max_num_workers 4 --machine_type n1-standard-2 --experiment enable_stackdriver_agent_metrics

