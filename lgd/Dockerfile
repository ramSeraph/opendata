ARG build_type
FROM ubuntu:22.04 as base-req-build
ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive
ENV helper_pkgs="equivs software-properties-common gnupg apt-utils"
RUN apt-get update && \
    apt install --no-install-recommends -y $helper_pkgs && \
    add-apt-repository ppa:alex-p/tesseract-ocr5 && \
    apt-get update && \
    equivs-control tesseract-ocr-eng.control && \
    equivs-control tesseract-ocr-osd.control && \
    sed -i 's/<package name; defaults to equivs-dummy>/tesseract-ocr-eng/g' tesseract-ocr-eng.control && \
    sed -i 's/<package name; defaults to equivs-dummy>/tesseract-ocr-osd/g' tesseract-ocr-osd.control && \
    sed -i 's/# Version: <enter version here; defaults to 1.0>/Version: 1:5.0.0/g' tesseract-ocr-eng.control && \
    sed -i 's/# Version: <enter version here; defaults to 1.0>/Version: 1:5.0.0/g' tesseract-ocr-osd.control && \
    cat tesseract-ocr-eng.control && \
    cat tesseract-ocr-osd.control && \
    equivs-build tesseract-ocr-eng.control && \
    equivs-build tesseract-ocr-osd.control && \
    dpkg -i tesseract-ocr-eng_5.0.0_all.deb && \
    dpkg -i tesseract-ocr-osd_5.0.0_all.deb && \
    dpkg-query -l | grep tesseract && \
    apt-get install --no-install-recommends -y python3 tesseract-ocr python3-pip python3-venv python-is-python3 && \
    apt-get -y --purge remove $helper_pkgs && \
    apt-get -y autoremove && \
    apt-get -y clean && \
    rm tesseract-ocr-* && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /venv

FROM base-req-build as base-final
RUN python -m venv /venv
COPY requirements.txt /requirements.txt
RUN  /venv/bin/pip install --no-cache-dir -r /requirements.txt
ENTRYPOINT ["/venv/bin/python"]

FROM base-${build_type} AS final
