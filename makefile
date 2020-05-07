## makefile automates the build and deployment for python projects

# type of project
PROJ_TYPE=	python

include ./zenbuild/main.mk

.PHONY:		testall
testall:	test
		make PY_SRC_TEST_PAT=defer_test_time.py test

.PHONY:		testconfig
testconfig:
		make PY_SRC_TEST_PAT=test_config.py test

.PHONY:		testpopulate
testpopulate:
		make PY_SRC_TEST_PAT=test_populate.py test

.PHONY:		testlog
testlog:
		make PY_SRC_TEST_PAT=test_log.py test

.PHONY:		testcli
testcli:
		make PY_SRC_TEST_PAT=test_cli.py test

testpersist:
		make PY_SRC_TEST_PAT=test_persist.py test

.PHONY:		testpersistattach
testpersistattach:
		make PY_SRC_TEST_PAT=test_persist_attach.py test

.PHONY:		testpersistfactory
testpersistfactory:
		make PY_SRC_TEST_PAT=test_persist_factory.py test

.PHONY:		testmulti
testmulti:
		make PY_SRC_TEST_PAT=test_multi_proc.py test
