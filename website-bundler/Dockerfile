FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

WORKDIR /code

RUN apt-get update && apt-get -y install curl

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=. \
    # pip:
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    # poetry:
    POETRY_NO_INTERACTION=1

COPY ./pyproject.toml ./poetry.lock /code/

RUN pip install -U poetry==2.1.4 \
  && poetry config virtualenvs.create false \
  && poetry install

RUN playwright install

RUN mkdir -p /code/c2/bundler && curl https://raw.githubusercontent.com/gildas-lormeau/SingleFile/refs/heads/master/lib/single-file.js -o /code/c2/bundler/single-file.js

COPY ./c2/ /code/c2/

CMD ["python3", "c2/bundler/main.py"]