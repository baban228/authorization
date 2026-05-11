FROM python:3.12-slim

WORKDIR /code

COPY ./requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./server ./server

EXPOSE 8000

CMD ["uvicorn", "server.cmd.server.main:app", "--host", "0.0.0.0", "--port", "8000"]