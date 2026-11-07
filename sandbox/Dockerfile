FROM python:3.12-slim
RUN useradd -m -u 10001 sandbox
WORKDIR /app
COPY runner.py /app/runner.py
USER sandbox
CMD ["python", "/app/runner.py"]