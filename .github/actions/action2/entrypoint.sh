#!/bin/sh -l

echo "From action 2 Hello $1"
time=$(date)
echo "time=$time" >> $GITHUB_OUTPUT

