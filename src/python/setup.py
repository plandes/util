from pathlib import Path
from zensols.pybuild import SetupUtil

su = SetupUtil(
    setup_path=Path(__file__).parent.absolute(),
    name="zensols.util",
    package_names=['zensols', 'resources'],
    package_data={'': ['*.conf']},
    description='Command line, configuration and persistence utilites generally used for any more than basic application.',
    user='plandes',
    project='util',
    keywords=['tooling'],
    has_entry_points=False,
).setup()
