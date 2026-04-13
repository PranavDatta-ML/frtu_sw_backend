#!/bin/bash

# Prompt to start or stop containers
read -p "Do you want to start or stop the containers? (start/stop) [start]: " ACTION
ACTION=${ACTION:-start}

# Validate action
if [[ $ACTION != "start" && $ACTION != "stop" ]]; then
  echo "Invalid action specified. Exiting."
  exit 1
fi

# Prompt to input and export HOST (IP address)
read -p "Enter the HOST (IP address) [DEFAULT - 127.0.0.1]: " HOST
HOST=${HOST:-127.0.0.1}
export HOST

# Prompt to input and export PORT
read -p "Enter the PORT [DEFAULT - 5000]: " PORT
PORT=${PORT:-5000}
export PORT

# Prompt to input APP_ENV_FILE
read -p "Enter the APP_ENV_FILE [DEFAULT - .sample.env]: " APP_ENV_FILE
APP_ENV_FILE=${APP_ENV_FILE:-.sample.env}

# Prompt for detached mode
read -p "Do you want to run in detached mode? (yes/no) [no]: " DETACHED
DETACHED=${DETACHED:-no}

# Prompt to include Postgres
read -p "Do you want to include Postgres service? (yes/no) [no]: " INCLUDE_POSTGRES
INCLUDE_POSTGRES=${INCLUDE_POSTGRES:-no}

# Prompt for PG_ENV_FILE if Postgres is included
if [[ $INCLUDE_POSTGRES == "yes" ]]; then
  read -p "Enter the PG_ENV_FILE [DEFAULT - .sample.pg.env]: " PG_ENV_FILE
  PG_ENV_FILE=${PG_ENV_FILE:-.sample.pg.env}
fi

# Prompt to input BROKER_ENV_FILE
read -p "Enter the BROKER_ENV_FILE [DEFAULT - .sample.broker.env]: " BROKER_ENV_FILE
BROKER_ENV_FILE=${BROKER_ENV_FILE:-.sample.broker.env}

# Build the service list
SERVICE_NAMES="web celery_worker rabbitmq"
if [[ $INCLUDE_POSTGRES == "yes" ]]; then
  SERVICE_NAMES+=" pg"
fi

# Build the docker-compose command
CMD="docker compose"
[[ $DETACHED == "yes" ]] && CMD+=" -d"

# Execute the command based on user action
if [[ $ACTION == "start" ]]; then
  $CMD up $SERVICE_NAMES
elif [[ $ACTION == "stop" ]]; then
  $CMD stop $SERVICE_NAMES
fi

# Display the exported variables
echo "HOST: $HOST"
echo "PORT: $PORT"
echo "APP_ENV_FILE: $APP_ENV_FILE"
echo "BROKER_ENV_FILE: $BROKER_ENV_FILE"
if [[ $INCLUDE_POSTGRES == "yes" ]]; then
  echo "PG_ENV_FILE: $PG_ENV_FILE"
fi
