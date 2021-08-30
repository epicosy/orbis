
from setuptools import setup, find_packages
from orbis.core.version import get_version

VERSION = get_version()

f = open('README.md', 'r')
LONG_DESCRIPTION = f.read()
f.close()

setup(
    name='orbis',
    version=VERSION,
    description='API Framework for benchmarking databases of faults for controlled testing studies',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='Eduard Pinconschi',
    author_email='eduard.pinconschi@tecnico.ulisboa.pt',
    url='https://github.com/epicosy/orbis',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'tests*']),
    package_data={'orbis': ['templates/*']},
    include_package_data=True,
    entry_points="""
        [console_scripts]
        orbis = orbis.main:main
    """,
)
