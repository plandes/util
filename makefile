## makefile automates the build and deployment for python projects

# type of project
PROJ_TYPE=	python

include ./zenbuild/main.mk

.PHONY:		testconfig
testconfig:
	make PY_SRC_TEST_PKGS=test_config.TestConfig test

.PHONY:		testpopulate
testpopulate:
	make PY_SRC_TEST_PKGS=test_populate.TestConfigPopulate test

.PHONY:		testconfigfactory
testconfigfactory:
	make PY_SRC_TEST_PKGS=test_configfactory.TestConfigFactory test

.PHONY:		testcli
testcli:
	make PY_SRC_TEST_PKGS=test_cli.TestActionCli test

.PHONY:		testpersist
testpersist:
	make PY_SRC_TEST_PKGS=test_persist.TestStash test

.PHONY:		testpersistfactory
testpersistfactory:
	make PY_SRC_TEST_PKGS=test_persist_factory.TestStashFactory test

.PHONY:		testmulti
testmulti:
	make PY_SRC_TEST_PKGS=test_multi_proc.TestMultiProc test
