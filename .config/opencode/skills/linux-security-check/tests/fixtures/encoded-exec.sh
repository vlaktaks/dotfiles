#!/bin/sh
# Harmless fixture: INERT. Never execute. Simulates base64-decoded execution.
payload="ZWNobyBoaQo="
printf '%s' "$payload" | base64 -d | sh
