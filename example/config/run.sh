#!/bin/sh

for i in $(find . -name \*.py -executable) ; do
    echo "running $i"
    ./$i
done

