FROM node:latest AS builder

WORKDIR /app/
COPY ./builder/package-lock.json ./builder/package.json .

RUN npm install

COPY ./builder/ .
COPY ./client/ ./src/
COPY ./c2/clients/plugins/ ./plugins/

RUN mkdir -p dist && mkdir -p flattened

RUN ["node", "builder.js"]


FROM python:3.13-slim

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

COPY ./c2/ /code/c2/

COPY --from=builder /app/dist/bundle.min.js /static/bundle.min.js

CMD ["fastapi", "run", "c2/clients/app.py"]