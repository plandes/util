"""Conditional branching logic configuration.

"""
__author__ = 'Paul Landes'

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
import logging
from zensols.persist import persisted
from . import ImportYamlConfig, ConfigurationError, Serializer

logger = logging.getLogger(__name__)


@dataclass
class _Condition(object):
    serializer: Serializer = field(repr=False)
    name: str
    ifn: Any
    thn: Dict[str, Any]
    eln: Dict[str, Any]
    parent: Dict[str, Any] = field(default=None, repr=False)

    @property
    @persisted('_child')
    def child(self) -> Dict[str, Any]:
        truthy = self.ifn
        if isinstance(truthy, str):
            truthy = self.serializer.parse_object(truthy)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'truth value: {self.ifn} ({self.ifn}) -> '
                         f'{truthy} ({truthy})')
        if truthy:
            node = None if self.thn is None else self.thn
        else:
            node = None if self.eln is None else self.eln
        return node[self.name]


class ConditionalYamlConfig(ImportYamlConfig):
    _CONDITION_NODE = 'condition'
    _IF_NODE = 'if'
    _THEN_NODE = 'then'
    _ELSE_NODE = 'else'

    def __init__(self, *args, condition_node: str = _CONDITION_NODE, **kwargs):
        super().__init__(*args, **kwargs)
        self._condition_node = condition_node
        self._evals: Dict[str, Dict[str, Any]] = {}

    def _find_node(self, n: Union[Dict, Any], path: str, name: str):
        if isinstance(n, _Condition):
            node = n.child
        else:
            node = super()._find_node(n, path, name)
        return node

    def _eval_tree(self, node: Dict[str, Any]):
        repls = {}
        for cn, cv in node.items():
            if isinstance(cv, _Condition):
                cond = cv
                repls[cond.name] = cond.child
            elif isinstance(cv, dict):
                self._eval_tree(cv)
        node.update(repls)
        node.pop(self._CONDITION_NODE, None)

    def get_tree(self, name: Optional[str] = None) -> Dict[str, Any]:
        node = self._evals.get(name)
        if node is None:
            node: Union[_Condition, Dict[str, Any]] = super().get_tree(name)
            if isinstance(node, dict):
                # we have to conditionally update recursively when a client
                # descends this tree without get_tree('(grand)child')
                self._eval_tree(node)
            self._evals[name] = node
        return node

    def _create_condition(self, node: Dict[str, Any]) -> _Condition:
        ifn = node.get(self._IF_NODE)
        thn = node.get(self._THEN_NODE)
        eln = node.get(self._ELSE_NODE)
        if ifn is None:
            raise ConfigurationError(
                f"Missing '{self._IF_NODE}' in condition: {node}")
        if thn is None and eln is None:
            raise ConfigurationError(
                f"Either '{self._THEN_NODE}' or " +
                f"'{self._ELSE_NODE}' must follow an if in: {node}")
        for cn, name in ((thn, self._IF_NODE), (eln, self._ELSE_NODE)):
            if cn is not None and len(cn) > 1:
                raise ConfigurationError(
                    'Conditionals can have only one child, ' +
                    f"but got {len(cn)}: {cn}'")
        thn_k = None if thn is None else next(iter(thn.keys()))
        eln_k = None if eln is None else next(iter(eln.keys()))
        if thn_k is not None and eln_k is not None and thn_k != eln_k:
            raise ConfigurationError(
                "Conditionals must have the same child root, got: '{node}'")
        return _Condition(self.serializer, thn_k or eln_k, ifn, thn, eln, node)

    def _map_conditions(self, par: Dict[str, Any], path: List[str]):
        add_conds = {}
        for cn, cv in par.items():
            if isinstance(cv, dict):
                if cn == self._condition_node:
                    cond = self._create_condition(cv)
                    add_conds[cond.name] = cond
                else:
                    path.append(cn)
                    self._map_conditions(cv, path)
                    path.pop()
        par.update(add_conds)

    def _compile(self) -> Dict[str, Any]:
        root = super()._compile()
        self._map_conditions(self._config, [])
        return root
