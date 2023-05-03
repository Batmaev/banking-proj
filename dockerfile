FROM alpine:latest

RUN apk update && apk add \
    bash \
    python3 \
    py3-pip \
    && pip3 install --upgrade pip

WORKDIR /app
COPY . .
RUN pip3 install -r requirements.txt
