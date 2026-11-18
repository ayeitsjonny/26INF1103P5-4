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

# Copy the automated test suite so it can run inside the container:
#   docker build -t reportapp .
#   docker run --rm reportapp python3 -m unittest discover -s tests -p "test_*.py" -v
COPY ./tests /app/tests

CMD ["python3", "main.py"]
