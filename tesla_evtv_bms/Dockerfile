ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache rsync

COPY rootfs /
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]