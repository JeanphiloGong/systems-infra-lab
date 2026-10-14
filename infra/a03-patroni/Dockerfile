FROM postgres:16@sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages 'patroni[etcd3]==4.1.5' 'psycopg[binary]==3.3.6'
