FROM python:3

WORKDIR /opt/apps/reranker
COPY . .
#ARG PIP_INDEX="--index https://pypi.doubanio.com/simple/"
RUN python -m pip install -r requirements.txt #${PIP_INDEX}
RUN pyinstaller --onefile server.py
RUN rm *.py

