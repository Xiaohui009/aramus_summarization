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

from util import get_summary_text_from_csv, get_arabic_summary, get_other_summary, get_ner_text_from_csv, \
    get_org_entity, filter_NER

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
        "Summarization": {
            "AGPTM": "AGPTM for Arabic summarization",
            "Llama3": "Open sourced LLM for English summarization",
        },
        "NER": {
            "AUTPM": "AUPTM NER",
        }
    }

    ret = {
        "models": configs,
        "status": 0,
        "running_time": time.time() - t1,
        "message": "",
    }
    return JSONResponse(ret)


example_input = {
    "file_path": "aramus-qa/upload/default/2024-05-15/ISO 55001.csv",
    "file_type": "pdf",
}


@app.post(
    "/summarize",
    tags=["AraMUS summarization"],
    summary="AraMUS summarization for quick demo",
)
async def summarize(request: Request, request_dict: JSONStructure = Body(..., example=example_input)) -> Response:
    """AraMUS summarization service, it utilizes AGPTM for Arabic summarization, and open source LLM for English
    summarization.

    The request should be a JSON object with `file_path` & `file_type` or `text` fields:
    - file_path: obs path [Optional]
    - file_type: `pdf`, `word` [Optional]
    - text: long string representing document content [Optional]
    """
    text_content = request_dict.get("text", None)
    file_path = request_dict.get("file_path", None)
    file_type = request_dict.get("file_type", None)
    model_type = request_dict.get("model_type", None)

    if model_type:
        model_type = model_type.strip().lower()
        if model_type not in {"llama3", "agptm"}:
            logging.info(f"Invalid model type {model_type}, use default `llama3`")
            model_type = 'llama3'

    request_id = str(uuid.uuid4())

    t1 = time.time()
    base_info = {
        "request_id": request_id,
        "file_path": file_path if file_path else None,
        "file_type": file_type if file_type else None,
        "text": text_content if text_content else None,
    }

    if not (file_path and file_type) and not text_content:
        ret = {
            "summary": None,
            "status": -1,
            "running_time": time.time() - t1,
            "message": "A valid obs file path  & file_type or text content must be provided.",
        }
        ret.update(base_info)
        return JSONResponse(ret)

    try:
        if text_content:
            text = text_content
        else:
            response = obsClient.getObject(
                BUCKET_NAME,
                file_path,
                loadStreamInMemory=True,
            )

            if response.status == 200:
                data = response.body.buffer
                data_io = StringIO(data.decode('utf-8'))
                csv_reader = csv.reader(data_io)
                text = get_summary_text_from_csv(
                    csv_reader=csv_reader,
                    file_type=file_type,
                )

            else:
                ret = {
                    "summary": None,
                    "status": -1,
                    "running_time": time.time() - t1,
                    "message": f"Something wrong during get {file_path} from OBS, status code {response.status}",
                }
                ret.update(base_info)
                return JSONResponse(ret)

        logging.info(f"Text: {text}")
        lan = detect(text=text)
        if 'ar' == lan and model_type not in ['llama3']:
            # Arabic text goes to AGPTM
            logging.info(f"Model type {model_type}, {file_path if not text_content else '<INPUT TEXT>'} calling AGPTM "
                         f"for summarization.")
            ret = get_arabic_summary(
                text=text,
            )
        else:
            # Other text goes to open source LLM
            logging.info(f"Model type {model_type}, {file_path if not text_content else '<INPUT TEXT>'} calling "
                         f"open-sourced LLM for summarization.")
            ret = get_other_summary(
                text=text,
                language="Arabic" if 'ar' == lan else "English",
            )
        ret.update(
            {
                "running_time": time.time() - t1,
            }
        )
        ret.update(base_info)
        return JSONResponse(ret)

    except Exception as e:
        logging.error(f"Exception while calling summarization: {str(e)}")
        logging.info(f"Traceback info: {traceback.format_exc()}")

        ret = {
            "summary": None,
            "status": -1,
            "running_time": time.time() - t1,
            "message": f"Exception while calling summarization: {str(e)}",
        }
        ret.update(base_info)
        return JSONResponse(ret)


@app.post(
    "/ner_tag",
    tags=["AraMUS NER"],
    summary="AraMUS NER tagging for quick demo",
)
async def ner_tag(request: Request, request_dict: JSONStructure = Body(..., example=example_input)) -> Response:
    """AraMUS NET tagging service, it utilizes AUPTM NER service to tag given content.

    The request should be a JSON object with `file_path` & `file_type` or `text` fields:
    - file_path: obs path [Optional]
    - file_type: `pdf`, `word` [Optional]
    - text: long string representing document content [Optional]
    """
    text_content = request_dict.get("text", None)
    file_path = request_dict.get("file_path", None)
    file_type = request_dict.get("file_type", None)
    filters = request_dict.get("filters", None)
    if filters:
        if isinstance(str, filters):
            filters = [filters]
    else:
        filters = []

    filter_set = {'NEOM', 'Neom', 'neom', 'wikipedia'}
    for _filter in filters:
        filter_set.add(_filter)

    request_id = str(uuid.uuid4())

    t1 = time.time()
    base_info = {
        "request_id": request_id,
        "file_path": file_path if file_path else None,
        "file_type": file_type if file_type else None,
        "text": text_content if text_content else None,
    }

    if not (file_path and file_type) and not text_content:
        ret = {
            "entity": None,
            "status": -1,
            "running_time": time.time() - t1,
            "message": "A valid obs file path  & file_type or text content must be provided.",
        }
        ret.update(base_info)
        return JSONResponse(ret)

    try:
        if text_content:
            text = text_content
        else:
            response = obsClient.getObject(
                BUCKET_NAME,
                file_path,
                loadStreamInMemory=True,
            )

            if response.status == 200:
                data = response.body.buffer
                data_io = StringIO(data.decode('utf-8'))
                csv_reader = csv.reader(data_io)
                text = get_ner_text_from_csv(
                    csv_reader=csv_reader,
                    file_type=file_type,
                )

            else:
                ret = {
                    "entity": None,
                    "status": -1,
                    "running_time": time.time() - t1,
                    "message": f"Something wrong during get {file_path} from OBS, status code {response.status}",
                }
                ret.update(base_info)
                return JSONResponse(ret)

        logging.info(f"Text: {text}")
        logging.info(f"{file_path if not text_content else '<INPUT TEXT>'} NER")
        ret = get_org_entity(text=text)
        logging.info(f"Raw NER: {ret}")
        entity = ret.get("entity", "")
        if entity:
            logging.info(f"NER filtering for {entity} in set {filter_set}")
            filtered_entity = filter_NER(entity=entity, candidates=filter_set)
            logging.info(f"Filtered entity: {filtered_entity}")
            ret.update(
                {
                    "entity": filtered_entity,
                }
            )

        ret.update(
            {
                "running_time": time.time() - t1,
            }
        )
        ret.update(base_info)
        return JSONResponse(ret)

    except Exception as e:
        logging.error(f"Exception while calling AUPTM NER tagging: {str(e)}")
        logging.info(f"Traceback info: {traceback.format_exc()}")

        ret = {
            "entity": None,
            "status": -1,
            "running_time": time.time() - t1,
            "message": f"Exception while calling AUPTM NER tagging: {str(e)}",
        }
        ret.update(base_info)
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
