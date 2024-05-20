# /usr/bin/env python

"""
@author: Xiaohui
@date: 2024/5/10
@filename: server.py
@description:
"""
import argparse
import json
import os
import time
import traceback
import uuid
import requests
from logger import get_logger

from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse, Response
from typing import Any, Dict, AnyStr, List, Union

from obs import GetObjectHeader
from obs import ObsClient
import traceback
from io import StringIO
import csv
from langdetect import detect

from util import get_text, get_arabic_summary, get_other_summary

logging = get_logger(os.path.basename(__file__))

app = FastAPI()

JSONObject = Dict[AnyStr, Any]
JSONArray = List[Any]
JSONStructure = Union[JSONArray, JSONObject]

ACCESS_KEY = "UERNBNVSGD0C638VBTY5"
SECRET_KEY = "7jVUYOwxvZEoRNtoo0Oq6uLwfXBTuxT8BBpeBqon"
BUCKET_NAME = "aramus-llm"
OBS_ENDPOINT = "http://obs.me-east-212.managedcognitivecloud.com"
obsClient = ObsClient(access_key_id=ACCESS_KEY, secret_access_key=SECRET_KEY, server=OBS_ENDPOINT)


@app.get("/health")
async def health() -> Response:
    """Health check."""

    return Response(status_code=200)


@app.get("/list_models")
async def list_models() -> Response:
    """List available model information."""
    t1 = time.time()
    configs = {
        "AGPTM": "AGPTM for Arabic summarization",
        "Llama3": "Open sourced LLM for English summarization",
    }

    ret = {
        "models": configs,
        "status": 0,
        "running_time": time.time() - t1,
        "message": "",
    }
    return JSONResponse(ret)


example_input = {
    "data_path": "aramus-qa/upload/default/2024-05-15/ISO 55001.csv",
}


@app.post(
    "/serve",
    tags=["AraMUS summarization"],
    summary="AraMUS summarization for quick demo",
)
async def serve(request: Request, request_dict: JSONStructure = Body(..., example=example_input)) -> Response:
    """AraMUS summarization service, it utilizes AGPTM for Arabic summarization, and open source LLM for English
    summarization.

    The request should be a JSON object with the following fields:
    - data_path: obs path
    """
    data_path = request_dict.get("data_path", None)

    request_id = str(uuid.uuid4())

    t1 = time.time()

    if not data_path:
        ret = {
            "request_id": request_id,
            "data_path": data_path if data_path else None,
            "summary": None,
            "status": -1,
            "running_time": time.time() - t1,
            "message": "A valid obs file path must be provided.",
        }
        return JSONResponse(ret)

    try:
        response = obsClient.getObject(
            BUCKET_NAME,
            data_path,
            loadStreamInMemory=True,
        )

        if response.status == 200:
            data = response.body.buffer
            data_io = StringIO(data.decode('utf-8'))
            csv_reader = csv.reader(data_io)
            text = get_text(csv_reader=csv_reader)
            logging.info(f"Text: {text}")
            lan = detect(text=text)
            if 'ar' == lan:
                # Arabic text goes to AGPTM
                logging.info(f"{data_path} is Arabic document, calling AGPTM for summarization.")
                ret = get_arabic_summary(
                    text=text,
                )
            else:
                # Other text goes to open source LLM
                logging.info(f"{data_path} is Non-Arabic document, calling open-sourced LLM for summarization.")
                ret = get_other_summary(
                    text=text,
                )
            ret.update(
                {
                    "request_id": request_id,
                    "data_path": data_path if data_path else None,
                    "running_time": time.time() - t1,
                }
            )
            return JSONResponse(ret)
        else:
            ret = {
                "request_id": request_id,
                "data_path": data_path if data_path else None,
                "summary": None,
                "status": -1,
                "running_time": time.time() - t1,
                "message": f"Something wrong during get {data_path} from OBS, status code {response.status}",
            }
            return JSONResponse(ret)

    except Exception as e:
        logging.error(f"Exception while calling AraMUS semantic matching: {str(e)}")
        logging.info(f"Traceback info: {traceback.format_exc()}")
        status = -1
        message = f"Exception while calling AraMUS semantic matching: {str(e)}"

        ret = {
            "request_id": request_id,
            "question": data_path if data_path else None,
            "summary": None,
            "status": status,
            "running_time": time.time() - t1,
            "message": message,
        }

        return JSONResponse(ret)


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port",
        type=int,
        help="Service port",
        default=3000
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Host IP",
        default="0.0.0.0"
    )
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
