setuptools-antlr
================

|Build Status| |Codecov Status| |Latest Release|

A ``setuptools`` command for generating ANTLR based parsers.

This is an extension for `setuptools <https://pypi.python.org/pypi/setuptools/>`__ integrating the famous `ANTLR <http://www.antlr.org/>`__ parser generator into the Python packaging process. It encapsulates the Java based generator of ANTLR and provides the user a single command to control the generation process.

All command line options of ANTLR are also available through the setuptools command. The user have the choice to pass the options on the command line or configure ANTLR in a default ``setup.cfg`` file.

ANTLR grammars and its dependencies like imported grammars or token files are automatically detected. For each root-level grammar a Python package will be generated during execution of the ``antlr`` command.

Installation
------------

``setuptools-antlr`` can be installed in various ways. To run it the following prerequisites have to be fulfilled:

- Python 3.5+
- setuptools 29.0.0+
- Java JRE 1.7+

The source distribution is already shipped with ANTLR 4.6. It isn't necessary to download ANTLR additionally.

After installation, the used Python environment has a new setuptools command called ``antlr``.

From Source Code
****************

::

    > git clone https://github.com/ferraith/setuptools-antlr.git
    > cd setuptools-antlr
    > pip install .

From PyPI
*********

::

    > pip install setuptools-antlr

From GitHub Releases
********************

::

    > pip install <setuptools-antlr_wheel>

Usage
-----

Integration
***********

.. code:: python

    setup(
        ...
        setup_requires=['setuptools-antlr'],
        install_requires=['antlr4-python3-runtime']
        ...
    )

Configuration
*************

Example
*******

.. |Build Status| image:: https://travis-ci.org/ferraith/setuptools-antlr.svg
   :target: https://travis-ci.org/ferraith/setuptools-antlr

.. |Codecov Status| image:: https://codecov.io/gh/ferraith/setuptools-antlr/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/ferraith/setuptools-antlr

.. |Latest Release| image:: https://img.shields.io/github/release/ferraith/setuptools-antlr.svg
   :target: https://github.com/ferraith/setuptools-antlr/releases
   :alt: Latest Release
