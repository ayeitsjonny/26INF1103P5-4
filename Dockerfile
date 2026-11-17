FROM alpine:3.24.2
RUN apk add --no-cache python3 py3-pip
WORKDIR /app

RUN python3 -m venv /opt/venv
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copies every .py file (models.py is new) plus the tests folder,
# so the tests can run inside the container as the brief requires.
COPY ./*.py /app/
COPY ./tests /app/tests

CMD ["python3", "main.py"]
