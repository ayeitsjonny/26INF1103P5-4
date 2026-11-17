FROM alpine:3.24.2
RUN apk add --no-cache python3 py3-pip
WORKDIR /app

RUN python3 -m venv /opt/venv
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all .py scripts into the image
COPY ./*.py /app/

CMD ["python3", "main.py"]
