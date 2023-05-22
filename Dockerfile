FROM tiangolo/uvicorn-gunicorn-fastapi
RUN apt update
RUN apt-get -y install curl gnupg
RUN curl -sL https://deb.nodesource.com/setup_14.x  | bash -
RUN apt-get -y install poppler-utils nodejs wget bash vim git nodejs jq
RUN npm install -g wikidata-taxonomy
RUN npm install -g wikibase-cli
COPY ./Semantics.py /app/
COPY ./conf /app/conf
COPY ./static/ /app/static
COPY ./app /app
COPY ./app/app.py /app/main.py
RUN pip install -r /app/requirements.txt
