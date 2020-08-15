## makefile automates the build and deployment for python projects

# type of project
PROJ_TYPE=	python
PROJ_MODULES=	git python-doc


include ./zenbuild/main.mk

.PHONY:		testall
testall:	test
		make PY_SRC_TEST_PAT=defer_test_time.py test

.PHONY:		testconfig
testconfig:
		make PY_SRC_TEST_PAT=test_config.py test

.PHONY:		testconfigwrite
testconfigwrite:
		make PY_SRC_TEST_PAT=test_config_write.py test

.PHONY:		testconfigstring
testconfigstring:
		make PY_SRC_TEST_PAT=test_config_str.py test

.PHONY:		testpopulate
testpopulate:
		make PY_SRC_TEST_PAT=test_populate.py test

.PHONY:		testlog
testlog:
		make PY_SRC_TEST_PAT=test_log.py test

.PHONY:		testdealloc
testdealloc:
		make PY_SRC_TEST_PAT=test_dealloc.py test

.PHONY:		testcli
testcli:
		make PY_SRC_TEST_PAT=test_cli.py test

.PHONY:		testpersist
testpersist:
		make PY_SRC_TEST_PAT=test_persist.py test

.PHONY:		testpersistattach
testpersistattach:
		make PY_SRC_TEST_PAT=test_persist_attach.py test

.PHONY:		testpersistfactory
testpersistfactory:
		make PY_SRC_TEST_PAT=test_persist_factory.py test

.PHONY:		teststash
teststash:
		make PY_SRC_TEST_PAT=test_stash.py test

.PHONY:		testmulti
testmulti:
		make PY_SRC_TEST_PAT=test_multi_proc.py test

.PHONY:		testdircomp
testdircomp:
		make PY_SRC_TEST_PAT=test_dircomp.py test

.PHONY:		testdictable
testdictable:
		make PY_SRC_TEST_PAT=test_dictable.py test
