#!/bin/bash
echo Scanning directory: $1
clamscan -v -r --log=/tmp/temp_log.txt $1