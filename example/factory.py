#!/usr/bin/env python

from zensols.config import ExtendedInterpolationEnvConfig, ImportConfigFactory
import domain

factory = ImportConfigFactory(ExtendedInterpolationEnvConfig('obj.conf'))
bob: domain.Person = factory('bob')
company: domain.Organization = factory('bob_co')
print(bob)
print(company)
print(id(company.boss) == id(bob))

school_clique: domain.Organization = factory('school_clique')
print(school_clique)

senior_company: domain.Organization = factory('bobs_senior_center')
print(senior_company)
