## makefile automates the build and deployment for python projects

# type of project
PROJ_TYPE=	python
PROJ_MODULES=	git python-doc python-doc-deploy

PY_SRC_TEST_PAT ?=	'test_impconfig.py'

include ./zenbuild/main.mk
