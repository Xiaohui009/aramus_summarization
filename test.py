# /usr/bin/env python

"""
@author: Xiaohui
@date: 2024/5/20
@filename: test.py
@description:
"""

from obs import GetObjectHeader
from obs import ObsClient
import traceback
from io import StringIO
import csv

if __name__ == "__main__":
    ak = "UERNBNVSGD0C638VBTY5"
    sk = "7jVUYOwxvZEoRNtoo0Oq6uLwfXBTuxT8BBpeBqon"
    bucketName = "aramus-llm"
    server = "http://obs.me-east-212.managedcognitivecloud.com"
    obsClient = ObsClient(access_key_id=ak, secret_access_key=sk, server=server)
    data_path = "aramus-qa/upload/default/2024-05-15/ISO 55001.csv"
    response = obsClient.getObject(bucketName, data_path, loadStreamInMemory=True)
    if response.status == 200:
        data = response.body.buffer
        data_io = StringIO(data.decode('utf-8'))
        csv_reader = csv.reader(data_io)
        sentence = []
        header = next(csv_reader)
        print(header)
        row1 = next(csv_reader)
        print(row1)
        for row in csv_reader:
            if row[1] != 'None':
                sentence.append(row[1] + '\n' + row[2])




