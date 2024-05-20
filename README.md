# FastAPI base service template
A template for quick deployment of fastAPI service. It serves as 
the boilerplate for further fastAPI service development. 

Do NOT change this code base. Rather, clone the code base and add
more functions to fit your customized service.

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