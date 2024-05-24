# /usr/bin/env python

"""
@author: Xiaohui
@date: 2024/5/24
@filename: test_api.py
@description:
"""
import csv
import os

import requests

if __name__ == "__main__":
    ret = list()
    file_list = {
        "Digital_Government_Strategy_2023-2030_ar.txt",
        "Commerce_ar.txt",
        "Geographic_Information_Systems _ar.txt",
        "Government_Budget_ar.txt",
        "Hajj_and_Umrah_ar.txt",
        "Industry_and_Mineral_Resources_ar.txt",
        "Justice_and_Judiciary _ar.txt",
        "Labor_and_Employment_ar.txt",
        "Municipal_Affairs_and_Housing_ar.txt",
        "Payment_Channels_ar.txt",
    }

    for fn in file_list:
        file_path = os.path.join("ar-docs", fn)
        print(f"Processing {file_path}")
        with open(file_path, "r", encoding="utf-8") as fp:
            texts = []
            count = 0
            for line in fp:
                line = line.strip()
                if len(line) < 1:
                    continue
                else:
                    texts.append(line)
                    count += 1
                if count > 5:
                    break
            payload = {
                "text": "\n".join(texts),
                "model_type":"llama3",

            }

            URL = f"http://localhost:3003/summarize"
            response = requests.post(
                url=URL,
                json=payload,
            )
            if response.status_code == 200:
                response_content = response.json()
                response_content.update(
                    {
                        "file_name": fn,
                    }
                )
                ret.append(response_content)

    with open("results.csv", "w", encoding="utf-8") as fp:
        csv_writer = csv.writer(fp)
        header = ["file_name", "text", "summary", "model_type"]
        csv_writer.writerow(header)
        for row in ret:
            csv_writer.writerow([row["file_name"], row["text"], row["summary"], row["model_type"]])