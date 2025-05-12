## makefile automates the build and deployment for python projects


## Build system
#
PROJ_TYPE=		python
PROJ_MODULES=		python/doc
ADD_CLEAN +=		example/config/counter.dat


## Includes
#
include ./zenbuild/main.mk


## Targets
#
.PHONY:			check
check:
			mypy src/python/zensols/introspect/imp.py

.PHONY:			runexamples
runexamples:
			( cd example/app ; ./fsinfo.py ls --format long > /dev/null 2>&1 )
			( cd example/app ; ./extharness.py > /dev/null 2>&1 )
			( cd example/config ; ./run.sh > /dev/null )
			( cd example/cli ; ./run.sh > /dev/null 2>&1 )

.PHONY:			testall
testall:		test runexamples

tmp:
			$(PY_PX_BIN) run testcur
