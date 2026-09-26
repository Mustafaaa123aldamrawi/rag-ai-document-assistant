FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt /app/requirements-api.txt
RUN python -m pip install --upgrade pip \
    && pip install -r /app/requirements-api.txt

COPY . /app

RUN python -m py_compile \
    api/main.py \
    api/auth_context.py \
    api/runtime_config.py \
    artifact_store.py \
    cloud_store.py \
    drawing_qa.py \
    drawing_visual.py \
    project_engineer.py \
    project_plan.py \
    project_dashboard.py \
    project_reports.py

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
