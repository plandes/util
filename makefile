## makefile automates the build and deployment for python projects


## Build system
#
PROJ_TYPE=		python
PROJ_MODULES=		python/doc python/package python/deploy
PY_TEST_ALL_TARGETS +=	testexamples
ADD_CLEAN +=		example/config/counter.dat


## Includes
#
include ./zenbuild/main.mk


## Targets
#
# show the output of the example
.PHONY:			showexample
showexample:		
			$(eval pybin := $(shell $(PY_PX_BIN) info --json | jq -r \
				'.environments_info|.[]|select(.name=="testcur").prefix' ))
			@export PYTHONPATH=$(abspath .)/src ; \
			 export PATH="$(pybin)/bin:$(PATH)" ; $(ARG)

# compare line output counts of examples as a poor man's integration test
.PHONY:			testexample
testexample:		
			@echo "running example: <<$(ARG)>>..."
			$(eval line_count := $(shell $(MAKE) $(PY_MAKE_ARGS) \
				ARG="$(ARG)" showexample | wc -l ) )
			@if [ $(line_count) -ne $(LINES) ] ; then \
				echo "Expecting $(LINES) but got $(line_count)" ; \
				exit 1 ; \
			fi
			@echo "running example: <<$(ARG)>>...ok"

# run all example
.PHONY:			testexamples
testexamples:
#			$(eval action := showexample)
			$(eval action := testexample)
			@$(MAKE) $(action) $(PY_MAKE_ARGS) LINES=4 \
				ARG="( cd example/app ; ./fsinfo.py ls --format long 2>&1 )"
			@$(MAKE) $(action) $(PY_MAKE_ARGS) LINES=35 \
				ARG="( cd example/config ; ./run.sh )"
			@$(MAKE) $(action) $(PY_MAKE_ARGS) LINES=47 \
				ARG="( cd example/cli ; ./run.sh 2>&1 )"

# this only works after the library is installed as it needs access to the
# package's resource library, which aren't relocatable
.PHONY:			extharnesstest
extharnesstest:
			@$(MAKE) $(action) $(PY_MAKE_ARGS) LINES=? \
				ARG="( cd example/app ; ./extharness.py )"
