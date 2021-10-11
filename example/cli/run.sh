#!/bin/sh

for i in $(seq 9) ; do
    if [ $i -ge 3 -a $i -lt 9 ] ; then
	cmd="-c payroll.conf"
    fi
    if [ $i -ge 9 ] ; then
	cmd="-c etc/payroll.conf"
    fi
    if [ $i -ge 4 ] ; then
	cmd="${cmd} show"
    fi
    if [ $i -eq 7 ] ; then
	cmd="${cmd} terse"
    fi
    echo "executing example $i: $cmd"
    ( cd $i-* ; ./main.py $cmd )
done
