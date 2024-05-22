# Summarization and NER service
This service calls AraMUS AGPTM for Arabic text summarization, Llama3 70B
for other language text. 

It also calls AraMUS AUPTM for entity extraction. For entity extraction,
it iterates the first several paragraphs, if there exists an ORG entity,
then it will be returned. It only returns the first occurrence of the ORG entity.

### How to run
```shell
python server [--host <host_ip>] [--port <port>]
```

### How to access swagger doc
```angular2html
http://<your_server_ip>/docs#/default
```

### Env setup
```shell
conda create -n <your_env_name> python=3.10

conda activate <your_env_name>

pip install -r requirements.txt
```