FROM python

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

RUN apt-get update && apt-get install -y wget unzip && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb && \
    apt-get clean


EXPOSE 8000

ENV LOGIN_URL="https://digitalport.mpa.gov.sg/"

ENV HEADLESS_MODE=true

ENV DEBUG_MODE=false

CMD [ "uvicorn", "app.digiport_scraper:app","--host", "0.0.0.0", "--port","8000" ]