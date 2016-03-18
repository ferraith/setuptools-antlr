"""Setup script for hello example."""
from distutils.command.build import build as _build
from setuptools import setup, find_packages
from antlr_distutils.build_antlr import build_antlr


class build(_build):
    sub_commands = _build.sub_commands + [
        ('build_antlr', None)
    ]

if __name__ == '__main__':
    setup(
        name='hello',
        version='0.1',
        description='Example of use of ANTLR',
        author='Andreas Schmidl',
        author_email='Andreas.Schmidl@gmail.com',
        packages=find_packages(),
        license='MIT',
        cmdclass={'build': build, 'build_antlr': build_antlr}
    )
