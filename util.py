# /usr/bin/env python

"""
@author: Xiaohui
@date: 2024/5/20
@filename: util.py
@description:
"""
import json
import os
import string
import time
import traceback

import requests

from logger import get_logger

logging = get_logger(os.path.basename(__file__))


def get_text(csv_reader, max_length=2048):
    text = list()
    current_length = 0
    last_block = ""

    # Skip header row
    header = next(csv_reader)
    for row in csv_reader:
        heading = "" if row[1] == 'None' or not row[1] else row[1]
        content = "" if row[2] == 'None' or not row[2] else row[2]
        heading = heading.translate(
            str.maketrans('', '', string.punctuation)
        )
        content = content.translate(
            str.maketrans('', '', string.punctuation)
        )
        heading_length = len(heading)
        content_length = len(content)

        if current_length + heading_length < max_length:
            text.append(heading)
            current_length += heading_length + 1
        else:
            last_block = heading
            break

        if current_length + content_length < max_length:
            text.append(content)
            current_length += content_length + 1
        else:
            last_block = content
            break

    cut_off = max_length - current_length - 9
    last_block = last_block.translate(
        str.maketrans('', '', string.punctuation)
    )
    last_block = last_block[:cut_off]

    text.append(last_block)

    return "\n".join(text)


AGPTM_SUMMARIZATION_URL = "http://37.224.68.137:9011/"


def get_arabic_summary(text):
    payload = {
        "document": text,
        "length": 128,
    }

    summary = None
    status = 0
    message = ""
    try:
        response = requests.post(
            url=AGPTM_SUMMARIZATION_URL,
            json=payload,
        )

        if response.status_code == 200:
            response_result = json.loads(response.content)
            summary = response_result["summary"]
        else:
            logging.error(f"No response from {AGPTM_SUMMARIZATION_URL}, status code = {response.status_code}")
            status = -1
            message = f"No response from {AGPTM_SUMMARIZATION_URL}, status code = {response.status_code}"
    except Exception as e:
        logging.error(f"Exception while calling AGPTM summarization {AGPTM_SUMMARIZATION_URL}. Exception {str(e)}")
        logging.info(f"Traceback info: {traceback.format_exc()}")
        status = -1
        message = f"Exception while calling AGPTM summarization {AGPTM_SUMMARIZATION_URL}. Exception {str(e)}"

    return {
        "summary": summary if status == 0 else None,
        "status": status,
        "message": message,
    }


def get_openai_model_id(base_url: str) -> str:
    url = f"{base_url}/v1/models"
    model_id = None
    try:
        response = requests.get(
            url=url,
        )
        if response.status_code == 200:
            data = response.json().get('data')
            if data:
                model_id = data[0].get("id")
                logging.info(f"model_id: {model_id}")
    except Exception as e:
        logging.error(f"Exception while getting model id from {url}: {str(e)}")
        model_id = None
    return model_id


LLM_BASE_URL = "http://localhost:3070"


def get_other_summary(text):
    summarization_prompt = """Your task is to generate a short summary of given text. Summarize the text below, 
delimited by triple backticks, in at most {max_length} words. Only summarize the given text, DO NOT put anything else
that are not the summary of the text!
 
Text: ```{text}```

Here is a summary of the text:
"""
    prompt = summarization_prompt.format(
        max_length=128,
        text=text,
    )
    payload = {
        "prompt": prompt,
        "max_tokens": 256,
        "temperature": 0.9,
        "repetition_penalty": 1.2,
        "stream": False,
        "top_k": 50,
        "top_p": 1,
        "stop_token_ids": [128009],
        "model": get_openai_model_id(base_url=LLM_BASE_URL),
    }

    URL = f"{LLM_BASE_URL}/v1/completions"
    summary = None
    status = 0
    message = ""
    try:
        response = requests.post(
            url=URL,
            json=payload,
        )
        if response.status_code == 200:
            response_content = response.json()
            summary = response_content["choices"][0]["text"]
        else:
            logging.error(f"No response from {URL}, status code = {response.status_code}")
            status = -1
            message = f"No response from {URL}, status code = {response.status_code}"
    except Exception as e:
        logging.error(f"Exception while calling LLM summarization {URL}. Exception {str(e)}")
        logging.info(f"Traceback info: {traceback.format_exc()}")
        status = -1
        message = f"Exception while calling LLM summarization {URL}. Exception {str(e)}"

    return {
        "summary": summary if status == 0 else None,
        "status": status,
        "message": message,
    }


if __name__ == "__main__":
    text_ar = "نيوم (بالإنجليزية: NEOM)‏ هو مشروع سعودي لمدينة مخطط لبنائها عابرة للحدود، أطلقه الأمير محمد بن سلمان " \
              "آل سعود، ولي العهد السعودي في يوم الثلاثاء 4 صفر 1439 هـ الموافق 24 أكتوبر 2017 ويقع المشروع في أقصى " \
              "شمال غرب المملكة العربية السعودية بـإمارة منطقة تبوك محافظة ضباء، ويمتد 460 كم على ساحل البحر الأحمر. " \
              "ويهدف المشروع ضمن إطار التطلعات الطموحة لرؤية 2030 بتحويل المملكة إلى نموذجٍ عالمي رائد في مختلف جوانب " \
              "الحياة، من خلال التركيز على استجلاب سلاسل القيمة في الصناعات والتقنية داخل المشروع وسيتم الانتهاء من " \
              "المرحلة الأولى لـ«نيوم» بحلول عام 2025م. تم دعم المشروع من قبل صندوق الاستثمارات العامة السعودي بقيمة " \
              "500 مليار دولار، والمستثمرين المحليين والعالميين. وتتولى «شركة نيوم» التي تأسست في يناير 2019 عمليات " \
              "تطوير منطقة نيوم والإشراف عليها، وهي شركة مساهمة مقفلة برأس مال مدفوع بالكامل وتعود ملكيتها إلى صندوق " \
              "الاستثمارات العامة. وستعمد الشركة إلى إنشاء مدن جديدة وبنية تحتية كاملة للمنطقة تشمل ميناءً، وشبكة " \
              "مطارات، ومناطق صناعية، ومراكز للإبداع لدعم الفنون، ومراكز للابتكار تدعم قطاع الأعمال، إضافة إلى تطوير " \
              "القطاعات الاقتصادية المستهدفة. وفي أكتوبر 2018 أعلن الرئيس التنفيذي للمشروع المهندس نظمي النصر عن " \
              "تشغيل أول مطار في نيوم قبل نهاية 2018، ثم تسيير رحلات إسبوعية إليه مع بداية عام 2019، على أن يكون " \
              "المطار واحدا من شبكة مطارات عدة سيتضمنها المشروع. وقد استقبل المطار الذي يحمل رمز مطار منظمة الطيران " \
              "المدني الدولي والواقع في «شرما» أول رحلة للخطوط السعودية في 10 يناير 2019، عبر طائرتين تجاريتين من " \
              "طراز إيرباص (آيه 320) تقلان 130 موظفا في المشروع. "
    summary_ar = get_arabic_summary(text=text_ar)
    print(f"Arabic summary: {summary_ar}")
    print("="*30)

    text_en = "ISO INTERNATIONAL STANDARD First edition 20140115 Asset management — Management systems — Requirements " \
              "Gestion d’actifs — Systèmes de management — Exigences Reference number ISO 550012014E Copyright " \
              "International Organization for Standardization Provided by SP Global under license with AENOR " \
              "LicenseeNEOM8275155001 UserCooksley Raymond No reproduction or networking permitted without license " \
              "from SP Global Not for Resale 01152023 045225 MST ©  ISO 550012014E COPYRIGHT PROTECTED DOCUMENT All " \
              "rights reserved Unless otherwise specified no part of this publication may be reproduced or utilized " \
              "otherwise in any form or by any means electronic or mechanical including photocopying or posting on " \
              "the internet or an intranet without prior written permission Permission can be requested from either " \
              "ISO at the address below or ISO’s member body in the country of the requester ISO copyright office " \
              "Email copyrightisoorg Web wwwisoorg Published in Switzerland Copyright International Organization for " \
              "Standardization Provided by SP Global under license with AENOR LicenseeNEOM8275155001 UserCooksley " \
              "Raymond No reprodu ict iion or networking permitted without license from SP Global Not for Resale " \
              "01152023 045225 MST © ISO 2014 – All rights reserved  ISO 550012014E Contents Page Foreword iv " \
              "Introduction v       41 Understanding the organization and its context 1 42 Understanding the needs " \
              "and expectations of stakeholders 1 43 Determining the scope of the asset management system2 44 Asset " \
              "management system 2  51 Leadership and commitment 2 52 Policy 3 53 Organizational roles " \
              "responsibilities and authorities3  61 Actions to address risks and opportunities for the asset " \
              "management system 3 62 Asset management objectives and planning to achieve them 4  71 Resources 5 72 " \
              "Competence 5 73 Awareness 6 74 Communication 6 75 Information requirements 6 76 Documented information " \
              "7  81 Operational planning and control 8 82 Management of change 8 83 Outsourcing8  91 Monitoring " \
              "measurement analysis and evaluation 8 92 Internal audit 9 93 Ma "
    summary_en = get_other_summary(text=text_en)
    print(f"English summary: {summary_en}")
