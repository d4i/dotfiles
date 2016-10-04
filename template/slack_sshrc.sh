#!/usr/bin/env bash

set -e

if [[ "${1}" = '--debug' ]]; then
  set -ux
else
  set -u
fi

CHANNEL='#home'
ME="$(whoami)"
USERNAME="${ME}@$(hostname)"
TEXT="$(who | grep -e "^${ME} \\+" | tail -1)"
ICON_EMOJI=':door:'
WEBHOOK_URL='https://hooks.slack.com/services/xxxxxxxxx/yyyyyyyyy/zzzzzzzzzzzzzzzzzzzzzzzz'

curl -S -s -X POST --data-urlencode \
  "payload={'channel': '${CHANNEL}', \
            'username': '${USERNAME}', \
            'text': '${TEXT}', \
            'icon_emoji': '${ICON_EMOJI}'}" \
  ${WEBHOOK_URL} > /dev/null