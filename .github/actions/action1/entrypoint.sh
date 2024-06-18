#!/bin/sh -l

echo "From action1 Hello $1"
time=$(date)
echo "time=$time" >> $GITHUB_OUTPUT

