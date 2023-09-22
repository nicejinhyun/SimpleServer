#FROM python:3
#ENV LANG C.UTF-8
#COPY run.sh /

#RUN apt-get update && apt-get -y install jq python3

#RUN pip install pyserial && \
#    pip install paho-mqtt

#RUN chmod a+x /run.sh

#CMD [ "/run.sh" ]

ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3

# Python 3 HTTP Server serves the current working dir
# So let's set it to our add-on persistent data directory.
WORKDIR /data

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
