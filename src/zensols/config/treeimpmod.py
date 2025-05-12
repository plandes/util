"""A factory class module to create deep nested dictionaries.

"""
__author__ = 'Paul Landes'

from typing import ClassVar, Any, Dict
from dataclasses import dataclass
from . import (
    Configurable, DictionaryConfig, FactoryError,
    ImportConfigFactoryModule, ModulePrototype, ImportConfigFactory,
)


@dataclass
class _TreeImportConfigFactoryModule(ImportConfigFactoryModule):
    """A module that creates an instance of an object from a deep nested
    configuration parsed by :class:`.TreeConfigurable`.

    The configuration string prototype has the form::

        tree[(<parameters>)]: <instance section name>

    The parameters must have a ``name`` entry with a dot (``.``) separate path
    in the :class:`.TreeConfigurable` data that selects the root to use for the
    instance.  The remainder of the parameters are provided to the initializer
    of the instance.

    """
    _NAME: ClassVar[str] = 'tree'

    def _instance(self, proto: ModulePrototype) -> Any:
        org_conf: Configurable = self.factory.config
        sec_name: str = proto.name
        params: Dict[str, Any] = proto.params
        config: Configurable = self.factory.config
        dconf = DictionaryConfig.from_config(config, deep=True)
        sec: Dict[str, Any] = dconf.get_tree(sec_name)
        if sec is None:
            raise FactoryError(f"No section to treeify: '{sec_name}'")
        dconf.config = {sec_name: sec}
        self.factory.config = dconf
        try:
            return self.factory.instance(**params)
        finally:
            self.factory.config = org_conf


ImportConfigFactory.register_module(_TreeImportConfigFactoryModule)
