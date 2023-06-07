"""Jupyter notebook utility and rendering classes.

"""
__author__ = 'Paul Landes'

from typing import Any, List, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import SubplotBase
import seaborn as sns
import pandas as pd
import IPython.display as ip
from zensols.config import ConfigFactory
from zensols.cli import NotebookHarness

logger = logging.getLogger()


@dataclass
class NotebookManager(object):
    """Bootstrap and import libraries to automate notebook testing.  It also
    contains utility methods for rendering data.  This class integrates with
    :class:`~zensols.cli.harness.NotebookHarness` to access Zensols applications
    via Jupyter.

    """
    package_resource: str = field()
    """See :obj:`~zensols.cli.harness.CliHarness.package_resource`."""

    app_root_dir: Path = field(default=Path('..'))
    """The application root directory."""

    src_dir_name: str = field(default='src/python')
    """See :obj:`~zensols.cli.harness.CliHarness.src_dir_name`."""

    default_section_name: str = field(default=None)
    """The name of the default section in the application config."""

    config: Path = field(default=None)
    """The configuration file name (no suffix)."""

    image_dir: Path = field(default=Path('../image'))
    """Where the images are stored."""

    def __post_init__(self):
        pass

    def __call__(self) -> NotebookHarness:
        """Return the application."""
        return self.get_application()

    def get_application(self) -> NotebookHarness:
        """Return the application."""
        return self['app']

    def __getitem__(self, name: str) -> Any:
        if not Path('resources').exists():
            logger.warning('no resources parent directory symbolic link found')
        return self.get_config_factory()(name)

    def _map_cli_arguments(self, **kwargs):
        """Convert args to override string.

        :param kwargs: arguments include: ``lang``, ``name``

        """
        args: List[str] = []
        sec: str = self.default_section_name
        if len(kwargs) > 0:
            ostr = ','.join(map(lambda kv: f'{sec}.{kv[0]}={kv[1]}',
                                kwargs.items()))
            args.extend(['--override', ostr])
        if self.config is not None:
            args.extend(['--config', str(self.config)])
        return args

    def get_config_factory(self) -> ConfigFactory:
        """Return the application."""

        return self.get_harness().get_config_factory(self._map_cli_arguments())

    def get_harness(self) -> NotebookHarness:
        """Create a new ``NotebookManager`` instance and return it."""
        return NotebookHarness(
            src_dir_name=self.src_dir_name,
            package_resource=self.package_resource,
            root_dir=self.app_root_dir,
            proto_factory_kwargs={
                'reload_pattern': f'^{self.package_resource}'})

    def display(self, *args, **kwargs):
        """Display an object in the notebook.

        :param args: arguments passed to :func:`IPython.display`

        :param kwargs: keyword arguments passed to :func:`IPython.display`

        """
        ip.display(*args, **kwargs)

    @staticmethod
    def subplots(rows: int = 1, cols: int = 1, pad: float = 5.,
                 height: int = None, width: int = 20, add_height: int = 0,
                 **kwargs) -> Union[SubplotBase, np.ndarray]:
        """Create the matplotlib plot axes using a tight layout.

        :param rows: the number of rows (each renders as a subpane)

        :param cols: the number of columns (each renders as a subpane)

        :param pad: the padding to add around the layout

        :param height: the row height; defaults to ``5 * (rows + add_height)``

        :param width: the column width

        :param add_height: the hight to add as a unit of the row height

        :param kwargs: additional keyword arguments to pass to
                       :function:`matplotlib.pyplot.plt.subplots`

        :return: an ``ax`` subplot, or an array of subplots if ``rows`` or
                 ``cols`` > 0

        """
        if height is None:
            height = 5 * (rows + add_height)
        fig, axs = plt.subplots(
            ncols=cols,
            nrows=rows,
            sharex=False,
            figsize=(width, height),
            **kwargs)
        fig.tight_layout(pad=pad)
        return axs

    def save_fig(self, ax: SubplotBase, name: str, image_format: str = 'svg'):
        """Save a plot to the reports directory in the provided format.

        :param ax: the (sub)plots that has the figure

        :param name: the name of the plot used in the file name
        """
        if self.image_dir is None:
            logger.info(f'no image directory set--skipping save of {name}')
        else:
            path: Path = self.image_dir / f'{name}.{image_format}'
            path.parent.mkdir(parents=True, exist_ok=True)
            fig = ax.get_figure()
            fig.savefig(path, format=image_format, bbox_inches='tight')
            logger.info(f'saved {path}')

    def heatmap(self, df: pd.DataFrame, pad: float = 9., add_height: float = 0,
                fmt: str = '.2f', title: str = None):
        """Create an annotation heat map for all windows and optionally normalize.

        """
        ax = self.subplots(1, 1, pad=pad, add_height=add_height)
        if title is not None:
            ax.set_title(title)
        return sns.heatmap(df, annot=True, fmt=fmt, ax=ax)
