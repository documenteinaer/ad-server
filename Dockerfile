# TODO: change this to -alpine later and add gcc and other required tools
FROM python:3.8.10-alpine
RUN mkdir /app
WORKDIR /app

# ADD requirements.txt /app
ADD airdocs-webserver.py /app/
ADD compare_signatures.py /app/
ADD utils.py /app/

ARG port
RUN echo Port exposed: ${port}
EXPOSE ${port}

# RUN pip3 install -r requirements.txt
RUN pip3 install numpy scipy sklearn
ENV airdocs_port=${port}
# CMD ["python3", "airdocs-webserver.py", "-l", "0.0.0.0", "-p 8081"]
CMD ["sh", "-c", "python3 airdocs-webserver.py -l 0.0.0.0 -p ${airdocs_port}"]

# TODO:
# HTTPS, limitare dimensiune documente -> Sa nu poti pune Gigs of data
