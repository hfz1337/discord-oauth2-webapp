FROM python:3.11

COPY requirements.txt .

RUN pip3 install -r requirements.txt && \
    rm -f requirements.txt

WORKDIR /app
COPY . ./

EXPOSE 5000

ENTRYPOINT [ "python3", "-u", "app.py" ]