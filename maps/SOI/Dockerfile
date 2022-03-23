FROM python:3.9.4

RUN echo "deb https://notesalexp.org/tesseract-ocr5/buster/ buster main" > /etc/apt/sources.list.d/notesalexp.list && \
    curl https://notesalexp.org/debian/alexp_key.asc | apt-key add - && \
    apt-get update && \
    apt-get install -y --no-install-recommends tesseract-ocr libgl1-mesa-glx libgdal-dev && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /code

RUN python -m venv /code/.venv

ENV PATH="/code/.venv/bin:${PATH}"

