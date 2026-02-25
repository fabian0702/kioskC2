FROM node:20-alpine AS build
WORKDIR /app

COPY ./frontend/package*.json ./

RUN npm ci

COPY ./frontend/ .

RUN npm run build -- --configuration production


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

COPY ./backend/pyproject.toml ./backend/poetry.lock /code/

RUN pip install -U poetry==2.1.4 \
  && poetry config virtualenvs.create false \
  && poetry install

COPY --from=build /app/dist/kiosk-frontend/browser /frontend/

COPY ./backend/c2/ /code/c2/

CMD ["python", "c2/backend/app.py"]