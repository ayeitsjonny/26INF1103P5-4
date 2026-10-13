from alpine:3.24.2
RUN apk add --no-cache python3 py3-pip
WORKDIR /app 

RUN python3 -m venv /opt/venv
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt /app/requirements.txt
COPY ./main.py ./io_manager.py ./ai_manager.py ./logic_manager.py ./data_manager.py /app/
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "main.py"]