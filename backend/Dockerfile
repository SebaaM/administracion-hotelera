FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home pms && mkdir -p media staticfiles && chown -R pms:pms /app
USER pms
