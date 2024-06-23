FROM ghcr.io/tna76874/docdepotbase:latest

COPY .git /app/.git
RUN git --git-dir=/app/.git rev-parse HEAD > COMMIT_HASH && \
    rm -rf /app/.git

COPY docdepot.py /app/docdepot.py
COPY helper.py /app/helper.py
COPY classify.py /app/classify.py
COPY docdepotdb.py /app/docdepotdb.py
COPY templates /app/templates
COPY ddclient /app/ddclient
RUN chmod -R +x /app

ENV DEPOSER_API_KEY='test'

EXPOSE 5000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["sh", "-c", "/app/entrypoint.sh"]