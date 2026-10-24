FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir psycopg2-binary==2.9.10
COPY generate_fake_data.py load_to_postgres.py ./
