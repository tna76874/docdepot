FROM python:3.9

WORKDIR /app

COPY docdepot.py /app/docdepot.py
COPY docdepotdb.py /app/docdepotdb.py
COPY templates /app/templates
COPY requirements.txt /app/requirements.txt

ENV DEPOSER_API_KEY='test'
RUN pip install pipreqs && pip install -r requirements.txt && chmod -R +x /app

EXPOSE 5000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["sh", "-c", "/app/entrypoint.sh"]
