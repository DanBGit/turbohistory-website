FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
ENV TH_DB=/data/subscribers.db
EXPOSE 8080
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8080","--proxy-headers"]
