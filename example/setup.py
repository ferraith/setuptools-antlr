"""Setup script for foobar example."""

if __name__ == '__main__':
    from setuptools import setup, find_packages

    setup(
        name='foobar',
        version='0.0.1',
        description='Example of use of ANTLR',
        author='Andreas Schmidl',
        author_email='Andreas.Schmidl@gmail.com',
        packages=find_packages(),
        setup_requires=['setuptools-antlr'],
        install_requires=['antlr4-python3-runtime']
    )
