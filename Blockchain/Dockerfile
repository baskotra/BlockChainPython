FROM python:3.8

COPY blockChain.py /app/
COPY requirements.txt /app/

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python","blockChain.py"]