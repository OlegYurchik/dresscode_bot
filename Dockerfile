FROM python:3.10-slim

WORKDIR /app

# Install requirements
RUN pip install poetry

COPY ./poetry.lock /app/poetry.lock
COPY ./pyproject.toml /app/pyproject.toml

RUN poetry install --only=main

COPY . /app

ENTRYPOINT ["poetry", "run", "python", "-m", "dresscode_bot"]
