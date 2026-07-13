#!/bin/bash
echo "============================================"
echo "  ALIOS ONE Chat - Community Edition"
echo "============================================"
command -v python3 >/dev/null || { echo "Python 3 not found — install it first."; exit 1; }
python3 -m pip install -r requirements.txt
if [ ! -f openrouter.key ]; then
  echo
  echo "Get a free API key at: https://openrouter.ai/keys"
  while true; do
    read -p "Paste your OpenRouter API key: " KEY
    KEY=$(echo "$KEY" | tr -d ' "')
    case "$KEY" in sk-*) break;; esac
    echo "That doesn't look like a valid key (should start with sk-). Try again."
  done
  echo "$KEY" > openrouter.key && chmod 600 openrouter.key
  echo "Key saved."
fi
echo
echo "Done! Start the app anytime with:  ./run.sh"
