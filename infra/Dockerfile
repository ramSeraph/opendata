FROM ubuntu:24.04 AS builder
RUN apt-get update
RUN apt-get install -y wget unzip
RUN wget https://github.com/jthomperoo/simple-proxy/releases/download/v1.2.0/simple-proxy_linux_amd64.zip
RUN unzip -d simple-proxy simple-proxy_linux_amd64.zip
RUN chmod a+x /simple-proxy/simple-proxy

FROM scratch
COPY --from=builder /simple-proxy/simple-proxy .
CMD ["/simple-proxy", "-logtostderr", "-v", "2", "-protocol", "https"]
