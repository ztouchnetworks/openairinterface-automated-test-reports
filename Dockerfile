FROM python:3.12-slim

# install python requirements
COPY ./requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

WORKDIR /app
CMD ["python", "/app/generate_oai_report.py", "--results_dir", "/target"]
