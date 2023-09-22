#!/bin/sh

CONFIG_FILE=/data/options.json
CONFIG_CONTROLLER=/share/SimplerServer/server.conf

CONFIG=`cat $CONFIG_FILE`

> $CONFIG_CONTROLLER

for i in $(echo $CONFIG | jq -r 'keys_unsorted | .[]')
do
  echo "[$i]" >> $CONFIG_CONTROLLER
  echo $CONFIG | jq --arg id "$i" -r '.[$id]|to_entries|map("\(.key)=\(.value|tostring)")|.[]' | sed -e "s/false/False/g" -e "s/true/True/g" >> $CONFIG_CONTROLLER