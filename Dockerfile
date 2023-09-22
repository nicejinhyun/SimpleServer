#ARG BUILD_FROM="alpine:latest"
FROM python:3

ENV LANG C.UTF-8

# Copy data for add-on
COPY run.sh

# Install requirements for add-on
RUN apt-get update && apt-get -y install jq python3

RUN pip install pyserial && \
    pip install paho-mqtt

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]