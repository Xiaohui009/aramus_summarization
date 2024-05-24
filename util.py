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
import platform

import nltk
from pyarabic import araby
import requests
from langdetect import detect
import Levenshtein
from logger import get_logger

logging = get_logger(os.path.basename(__file__))


def get_heading_and_content(csv_row, file_type):
    if file_type in ['pdf']:
        heading = "" if csv_row[1] == 'None' or not csv_row[1] else csv_row[1]
        content = "" if csv_row[2] == 'None' or not csv_row[2] else csv_row[2]
    elif file_type in ['word']:
        heading = ""
        for idx in range(1, 5):
            heading += "" if csv_row[idx] == 'None' or not csv_row[idx] else csv_row[idx]
        content = "" if csv_row[5] == 'None' or not csv_row[5] else csv_row[5]
    else:
        heading = ""
        content = ""

    return heading, content


def get_summary_text_from_csv(csv_reader, file_type, max_length=2048):
    text = list()
    current_length = 0
    last_block = ""

    # Skip header row
    header = next(csv_reader)
    for row in csv_reader:
        heading, content = get_heading_and_content(
            csv_row=row,
            file_type=file_type,
        )

        heading = heading.translate(
            str.maketrans('', '', string.punctuation)
        )
        content = content.translate(
            str.maketrans('', '', string.punctuation)
        )

        heading_length = len(heading)
        content_length = len(content)

        if current_length + heading_length < max_length:
            if heading:
                text.append(heading)
                current_length += heading_length + 1
        else:
            last_block = heading
            break

        if current_length + content_length < max_length:
            if content:
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
            logging.error(
                f"No response from AGPTM summarization endpoint {AGPTM_SUMMARIZATION_URL}, status code = {response.status_code}")
            status = -1
            message = f"No response from AGPTM summarization endpoint {AGPTM_SUMMARIZATION_URL}, status code = {response.status_code}"
    except Exception as e:
        logging.error(
            f"Exception while calling AGPTM summarization endpoint {AGPTM_SUMMARIZATION_URL}. Exception {str(e)}")
        logging.info(f"Traceback info: {traceback.format_exc()}")
        status = -1
        message = f"Exception while calling AGPTM summarization endpoint {AGPTM_SUMMARIZATION_URL}. Exception {str(e)}"

    return {
        "summary": summary if status == 0 else None,
        "status": status,
        "message": message,
    }


def get_ner_text_from_csv(csv_reader, file_type, max_length=42):
    texts = list()
    # Skip header row
    header = next(csv_reader)

    for row in csv_reader:
        heading, content = get_heading_and_content(
            csv_row=row,
            file_type=file_type,
        )

        if len(texts) < max_length and heading:
            texts.append(heading)
        if len(texts) < max_length and content:
            texts.append(content)

    text = "\n".join(texts)

    return text


AUPTM_NER_URL = "http://37.224.68.138:8030/"


def get_org_entity(text, max_sentences=19):
    lang = detect(text=text)
    if lang in ['ar']:
        sentences = araby.sentence_tokenize(text)
        logging.info(f"Number of Arabic sentences: {len(sentences)}")
    else:
        sentences = nltk.tokenize.sent_tokenize(text, language='english')
        logging.info(f"Number of English sentences: {len(sentences)}")

    sentences = sentences[:max_sentences]
    ret = list()

    status = 0
    message = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        logging.info(f"Extracting entities from {sentence}")

        payload = {
            "sentence": sentence,
        }
        try:
            response = requests.post(
                url=AUPTM_NER_URL,
                json=payload,
            )

            if response.status_code == 200:
                response_result = json.loads(response.content)
                entities = response_result["entities"]

                for entity in entities:
                    logging.info(f"Entity type: {entity['label']}, mention: {entity['mention']}")
                    if entity['label'] in ['ORG']:
                        ret.append(entity['mention'])
            else:
                logging.error(
                    f"No response from AUPTM NER endpoint {AUPTM_NER_URL}, status code = {response.status_code}")
                status = -1
                message = f"No response from AUPTM NER endpoint {AUPTM_NER_URL}, status code = {response.status_code}"
        except Exception as e:
            logging.error(
                f"Exception while calling AUPTM NER endpoint {AUPTM_NER_URL}. Exception {str(e)}")
            logging.info(f"Traceback info: {traceback.format_exc()}")
            status = -1
            message = f"Exception while calling AUPTM NER endpoint {AGPTM_SUMMARIZATION_URL}. Exception {str(e)}"

    return {
        "status": status,
        "entity": ret[0] if ret else "",
        "message": "" if ret else message,
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


# Llama3 70B openAI style API
LLM_BASE_URL = "http://192.168.0.13:3070" if platform.system().lower() in ['linux'] else "http://localhost:3070"


def get_other_summary(text, lan='en'):
    system_prompt = "Summarize the context in less than 10 sentences. If the context is in Arabic, the summary must " \
                    "be in Arabic as well. DO NOT put anything else that are not the summary of the text! "

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": """Context: {text}. Summary{language}: """.format(text=text,
                                                                         language=" in Arabic" if lan in ['ar'] else "")
        }
    ]
    payload = {
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.0,
        "stream": False,
        "stop_token_ids": [128009],
        "model": get_openai_model_id(base_url=LLM_BASE_URL),
    }

    URL = f"{LLM_BASE_URL}/v1/chat/completions"
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
            summary = response_content["choices"][0]['message']['content']
        else:
            logging.error(f"No response from Llama3 endpoint {URL}, status code = {response.status_code}")
            status = -1
            message = f"No response from Llama3 endpoint {URL}, status code = {response.status_code}"

    except Exception as e:
        logging.error(f"Exception while calling Llama3 endpoint {URL}. Exception {str(e)}")
        logging.info(f"Traceback info: {traceback.format_exc()}")
        status = -1
        message = f"Exception while calling Llama3 endpoint {URL}. Exception {str(e)}"

    return {
        "summary": summary if status == 0 else None,
        "status": status,
        "message": message,
    }


def get_other_summary2(text, lan='en'):
    summarization_prompt_en = """Your task is to generate a short summary of given text. Summarize the text below, 
delimited by triple backticks, in at most {max_length} words. Only summarize the given text, DO NOT put anything else
that are not the summary of the text! Your response must be in the same language with the text.

Text: ```{text}```

Here is a summary of the text:
"""
    summarization_prompt_ar = """مهمتك هي إنشاء ملخص قصير للنص المحدد. قم بتلخيص النص أدناه، مع تحديده بعلامات نقر 
    ثلاثية، بكلمات يبلغ عددها {max_length} على الأكثر. قم بتلخيص النص المحدد فقط، ولا تضع أي شيء آخر ليس ملخصًا للنص! 
    يجب أن يكون ردك بنفس لغة النص. 

النص: ```{text}```

يرجى الإخراج باللغة العربية:
"""
    summarization_prompt = summarization_prompt_ar if lan in ['ar'] else summarization_prompt_en
    logging.info(f"lan={lan}, prompt in {'Arabic' if lan in ['ar'] else 'English'}")
    prompt = summarization_prompt.format(
        max_length=128,
        text=text,
    )
    payload = {
        "prompt": prompt,
        "max_tokens": 256,
        "temperature": 0,
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
            logging.error(f"No response from Llama3 endpoint {URL}, status code = {response.status_code}")
            status = -1
            message = f"No response from Llama3 endpoint {URL}, status code = {response.status_code}"
    except Exception as e:
        logging.error(f"Exception while calling Llama3 endpoint {URL}. Exception {str(e)}")
        logging.info(f"Traceback info: {traceback.format_exc()}")
        status = -1
        message = f"Exception while calling Llama3 endpoint {URL}. Exception {str(e)}"

    return {
        "summary": summary if status == 0 else None,
        "status": status,
        "message": message,
    }


def filter_NER(entity, candidates):
    if entity in candidates or not candidates:
        return entity

    results = list()
    for candidate in candidates:
        d = Levenshtein.distance(entity, candidate)
        results.append((candidate, d))

    results = sorted(results, key=lambda x: x[1], reverse=False)
    threshold = int(len(entity) * 0.3)
    ret, min_dist = results[0]
    if min_dist > threshold:
        ret = ""

    return ret


def load_predefined_entity(fn="entities.txt"):
    entity_dict = dict()
    logging.info(f"Loading predefined entity from {fn}")
    with open(fn, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if len(line) > 0:
                key = line.lower()
                value = line
                entity_dict[key] = value

    logging.info(f"{len(entity_dict)} entities loaded")

    return entity_dict


ENTITY_LOOKUP_TABLE = load_predefined_entity()

if __name__ == "__main__":
    text_ar = "ليلى هي فتاة سعودية جميلة وذكية تعيش في مدينة الرياض مع عائلتها وكانت تدرس في إحدى المدارس الخاصة " \
              "الرائدة في المدينة. كانت ليلى تحب القراءة والكتابة، وكانت تميل دائمًا إلى البحث عن المعلومات وتوسيع " \
              "معرفتها.  كانت تحب الاطلاع على كل ما هو جديد في مجال العلوم والتكنولوجيا والثقافة. كانت ليلى دائمًا " \
              "مليئة بالحيوية والنشاط، وكانت تشارك في العديد من الأنشطة الرياضية والثقافية في مدرستها. عندما تخرجت " \
              "ليلى من المدرسة قررت الانتقال إلى جامعة في الولايات المتحدة الأمريكية لمواصلة دراستها. كانت هذه خطوة " \
              "كبيرة بالنسبة لليلى، ولكنها كانت مستعدة للتحدي والاستكشاف والتعلم. بدأت ليلى دراسة العلوم الحاسوبية في " \
              "الجامعة، وكانت تعمل بجد لتحقيق أهدافها الأكاديمية. كانت تلتقي بزملائها الدراسيين والأساتذة وتتعلم " \
              "منهم، وكانت تشارك في العديد من الفعاليات الثقافية والاجتماعية التي تنظمها الجامعة وكونت من خلالها على " \
              "الكثير من الصداقات. "
    summary_ar = get_arabic_summary(text=text_ar)
    print(f"Arabic summary by AGPTM: {summary_ar}")
    print("=" * 30)

    summary_ar = get_other_summary(text=text_ar, lan='ar')
    print(f"Arabic summary by LLaMA3: {summary_ar}")
    print("=" * 30)

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
    print("=" * 30)

    org_entity = get_org_entity(text_ar)
    print(f"Org entity for Arabic text: {org_entity}")
    print("=" * 30)

    org_entity = get_org_entity(text_en)
    print(f"Org entity for English text: {org_entity}")
    print("=" * 30)

    entity = filter_NER(
        entity=" ماانواع ال انتخابات,",
        candidates={"wikipedia hospital", 'wikipedia', 'ماانواع الانتخابات'},
    )
    print(f"Entity: {entity}")
    print("=" * 30)
