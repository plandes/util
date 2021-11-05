#!/usr/bin/env python

from zensols.config import ImportIniConfig, ImportConfigFactory
import domain

factory = ImportConfigFactory(ImportIniConfig('imp.conf'))
company: domain.Organization = factory('bobs_youth_center')
print(f"homer's new age: {company.boss.age}")
company.write()
