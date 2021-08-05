## makefile automates the build and deployment for python projects

# type of project
PROJ_TYPE=		python
PROJ_MODULES=		git python-doc python-doc-deploy python-resources
CLEAN_ALL_DEPS +=	cleanexample

#PY_SRC_TEST_PAT ?=	'test_action.py'

include ./zenbuild/main.mk


.PHONY:			cleanexample
cleanexample:
			find example -type d -name __pycache__ \
			  -prune -exec rm -r {} \;

.PHONY:			check
check:
			mypy src/python/zensols/introspect/imp.py
