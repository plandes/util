## makefile automates the build and deployment for python projects

# type of project
PROJ_TYPE=		python
PROJ_MODULES=		git python-doc python-doc-deploy python-resources
CLEAN_DEPS +=		pycleancache
ADD_CLEAN +=		example/config/counter.dat

#PY_SRC_TEST_PAT ?=	'test_impconfig.py'

include ./zenbuild/main.mk


.PHONY:			check
check:
			mypy src/python/zensols/introspect/imp.py

.PHONY:			runexamples
runexamples:
			( cd example/app ; ./fsinfo.py ls --format long )
			( cd example/config ; ./run.sh )
			( cd example/cli ; ./run.sh )

.PHONY:			testall
testall:		test runexamples
