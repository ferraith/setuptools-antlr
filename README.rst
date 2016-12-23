setuptools-antlr
================

|Build Status| |Codecov Status| |Latest Release|

A ``setuptools`` command for generating ANTLR based parsers.

This is an extension for `setuptools <https://pypi.python.org/pypi/setuptools/>`__ integrating the famous `ANTLR <http://www.antlr.org/>`__ parser generator into the Python packaging process. It encapsulates the Java based generator of ANTLR and provides the user a single command to control the generation process.

All command line options of ANTLR are also available through the setuptools command. The user have the choice to pass the options on the command line or configure ANTLR in a dedicated section in the ``setup.cfg`` file.

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

For a smooth user experience it's recommended to pass ``setuptools-antlr`` using the ``setup_requires`` argument of setup function. Additionally each generated parser requires the ANTLR runtime library which should be added to ``install_requires`` argument:

.. code:: python

    setup(
        ...
        setup_requires=['setuptools-antlr'],
        install_requires=['antlr4-python3-runtime']
        ...
    )

Before generating a parser ``setuptools`` will automatically check the Python environment and download ``setuptools-antlr`` from `PyPI <https://pypi.python.org>`__ if it's missing. During the installation of the project package ``pip`` will install ``antlr4-python3-runtime`` into the Python environment.

Configuration
*************

``setuptools-antlr`` provides two possibilities to configure the ANTLR parser generator.

All options of ANTLR can be passed on the command line after the ``antlr`` command:

::

    > python setup.py antlr --visitor

It's also possible to pass several options to ANTLR or execute multiple commands at once:

::

    > python setup.py antlr --visitor --grammar-options "superClass=Abc tokenVocab=SomeLexer" bdist_wheel

See ``python setup.py antlr --help`` for available command line options:

::

    > python setup.py antlr --help
    ...
    Options for 'AntlrCommand' command:
      --build-lib (-d)   directory to "build" (copy) to
      --atn              generate rule augmented transition network diagrams
      --encoding         specify grammar file encoding e.g. euc-jp
      --message-format   specify output style for messages in antlr, gnu, vs2005
      --long-messages    show exception details when available for errors and
                         warnings
      --listener         generate parse tree listener (default)
      --no-listener      don't generate parse tree listener
      --visitor          generate parse tree visitor
      --no-visitor       don't generate parse tree visitor (default)
      --depend           generate file dependencies
      --grammar-options  set/override a grammar-level option
      --w-error          treat warnings as error
      --x-dbg-st         launch StringTemplate visualizer on generated code
      --x-dbg-st-wait    wait for STViz to close before continuing
      --x-force-atn      use the ATN simulator for all predictions
      --x-log            dump lots of logging info to antlr-<timestamp>.log
    ...

The ANTLR documentation explains all `command line options <https://github.com/antlr/antlr4/blob/master/doc/tool-options.md>`__ and `grammar options <https://github.com/antlr/antlr4/blob/master/doc/options.md>`__ in detail.

Apart from passing options on the command line it's also possible to add a dedicated ``[antlr]`` section to ``setup.cfg``. The following example section contains all available options:

.. code:: ini

    [antlr]
    # Generate DOT graph files that represent the internal ATN data structures (yes|no); default: no
    #atn = no
    # Specify grammar file encoding (default: utf-8)
    #encoding = utf-8
    # Specify output style for messages in antlr (antlr|gnu|vs2005); default: antlr
    #message-format = antlr
    # Show exception details when available for errors and warnings (yes|no); default: no
    #long-messages = no
    # Generate a parse tree listener (yes|no); default: yes
    #listener = yes
    # Generate parse tree visitor (yes|no); default: no
    visitor = yes
    # Generate file dependencies (yes|no); default: no
    #depend = no
    # Set/override grammar-level options (<option>=<value> [<option>=value ...]); default: language=Python3
    grammar-options = superClass=Abc
                      tokenVocab=SomeLexer
    # Treat warnings as errors (yes|no); default: no
    #w-error = no
    # Launch StringTemplate visualizer on generated code (yes|no); default: no
    #x-dbg-st = no
    # Wait for STViz to close before continuing
    #x-dbg-st-wait = no
    # Use the ATN simulator for all predictions (yes|no); default: no
    #x-force-atn = no
    # Dump lots of logging info to antlr-<timestamp>.log (yes|no); default: no
    #x-log = no

Example
*******

Alongside the ``setuptools-antlr`` source code a example project called ``foobar`` is provided in the ``example`` directory. This example consists of the two ANTLR grammars ``Foo`` and ``Bar``. During the execution of ``setuptools-antlr`` two Python packages will be generated into the ``build`` directory containing a parser for each grammar.

To generate  parsers for all root-level grammars and build a ``foobar`` wheel package execute the following command:

::

    > python setup.py antlr bdist_wheel

.. |Build Status| image:: https://travis-ci.org/ferraith/setuptools-antlr.svg
   :target: https://travis-ci.org/ferraith/setuptools-antlr

.. |Codecov Status| image:: https://codecov.io/gh/ferraith/setuptools-antlr/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/ferraith/setuptools-antlr

.. |Latest Release| image:: https://img.shields.io/github/release/ferraith/setuptools-antlr.svg
   :target: https://github.com/ferraith/setuptools-antlr/releases
   :alt: Latest Release
