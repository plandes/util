"""Downloads files with a progress bar.

Inspired by `this thread <https://stackoverflow.com/questions/15644964/python-progress-bar-and-downloads>`_.

"""

from typing import Dict, Any
from dataclasses import dataclass, field
import logging
from pathlib import Path
import urllib.request
from tqdm import tqdm

logger = logging.getLogger(__name__)


class _DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


@dataclass
class Downloader(object):
    """A utility class to download a file and (optionally) display a progress bar
    as it downloads.

    """
    use_progress_bar: bool = field(default=True)
    """Whether or not to render the progress bar as the file downloads."""

    skip_if_exists: bool = field(default=True)
    """Skip download if the file exists as the target path."""

    mkdir: bool = field(default=True)
    """Recursively create directories for the target path if they do not already
    exist.

    """

    tqdm_params: Dict[str, Any] = field(
        default_factory=lambda: {'unit': 'B', 'unit_scale': True})
    """Parameters given to :mod:`tqdm` for the progress bar when downloading.

    """
    def download(self, url: str, output_path: Path):
        if self.skip_if_exists and output_path.is_file():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'{output_path} is already downloaded')
        else:
            parent = output_path.parent
            if self.mkdir and not parent.is_dir():
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f'creating directory: {parent}')
                parent.mkdir(parents=True)
            if logger.isEnabledFor(logging.INFO):
                logger.info(f'downloading vocab from {url} to {output_path}')
            params = dict(self.tqdm_params)
            params.update({'miniters': 1, 'desc': url.split('/')[-1]})
            if self.use_progress_bar:
                with _DownloadProgressBar(**params) as t:
                    urllib.request.urlretrieve(
                        url, filename=output_path, reporthook=t.update_to)
            else:
                urllib.request.urlretrieve(url, filename=output_path)
