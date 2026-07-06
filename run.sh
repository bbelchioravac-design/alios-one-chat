#!/bin/bash
( sleep 2; xdg-open http://localhost:8801 2>/dev/null || open http://localhost:8801 2>/dev/null ) &
python3 server.py
