FROM apache/beam_python3.8_sdk:2.35.0

RUN echo "deb https://notesalexp.org/tesseract-ocr5/buster/ buster main" > /etc/apt/sources.list.d/notesalexp.list && \
    curl https://notesalexp.org/debian/alexp_key.asc | apt-key add - && \
    apt-get update && \
    apt-get install -y tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*


COPY requirements.txt /tmp/lgd/requirements.txt

RUN pip install --no-deps -r /tmp/lgd/requirements.txt && rm -rf /root/.cache/pip

COPY scrape/captcha/models/ /lgd_models/

COPY *.py /tmp/lgd/
COPY scrape/*.py /tmp/lgd/scrape/
COPY scrape/captcha/*.py /tmp/lgd/scrape/captcha/

RUN cd /tmp/lgd/ && python setup.py sdist && pip install dist/lgd-0.0.1.tar.gz && rm -rf ./*

RUN python -c "from scrape.captcha_helper import CaptchaHelper; CaptchaHelper.prepare('/lgd_models/')"
