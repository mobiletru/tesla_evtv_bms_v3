ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache can-utils iproute2 python3 py3-pip

COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

COPY app /app/app
COPY run.sh /
RUN chmod a+x /run.sh

WORKDIR /app
CMD [ "/run.sh" ]
