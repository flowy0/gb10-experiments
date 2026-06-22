#!/bin/bash
# Start crw - Firecrawl-compatible web scraper
# Runs on port 3002
cd /opt/atom
nohup /opt/atom/crw/target/release/crw serve --port 3002 > /tmp/crw.log 2>&1 &
echo "crw started on port 3002 (PID: $!)"
