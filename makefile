## makefile automates the build and deployment for python projects

# type of project
PROJ_TYPE=	python
PROJ_MODULES=	git python-doc python-doc-deploy python-resources

#PY_SRC_TEST_PAT ?=	'test_ocli.py'

include ./zenbuild/main.mk
