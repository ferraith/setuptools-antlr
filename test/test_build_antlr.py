from distutils.dist import Distribution
from os import chdir, environ, path
from pathlib import Path

import pytest

from antlr_distutils.build_antlr import AntlrGrammar, build_antlr


@pytest.fixture(scope="module", autouse=True)
def ch_resources_dir():
    localdir = path.dirname(__file__)
    chdir(path.join(localdir, 'resources'))


def test_antlr_grammar_read_with_imports():
    grammar = AntlrGrammar(Path('SomeGrammar.g4'))
    imports = set(grammar.read_imports())

    assert len(imports) == 2
    assert {'CommonTerminals', 'SharedRules'} == imports


def test_antlr_grammar_read_without_imports():
    grammar = AntlrGrammar(Path('CommonTerminals.g4'))
    imports = grammar.read_imports()

    assert not imports


def test_antlr_grammar_read_nonexistent_file(capsys):
    grammar = AntlrGrammar(Path('FooBar.g4'))
    imports = grammar.read_imports()

    # check if error was logged
    _, err = capsys.readouterr()
    assert 'FooBar.g4' in err
    assert not imports


def test_build_antlr_find_java_valid_java_home(mocker):
    dist = Distribution()
    command = build_antlr(dist)

    mocker.patch.dict('os.environ', {'JAVA_HOME': 'c:/path/to/java'})
    mocker.patch('antlr_distutils.build_antlr.which', return_value='c:/path/to/java/bin/java.exe')
    mocker.patch.object(build_antlr, '_validate_java', return_value=True)

    java_path = command._find_java()
    assert java_path == Path('c:/path/to/java/bin/java.exe')


def test_build_antlr_find_java_invalid_java_home(mocker):
    dist = Distribution()
    command = build_antlr(dist)

    mocker.patch.dict('os.environ', {'JAVA_HOME': 'c:/path/to/java'})
    mocker.patch('antlr_distutils.build_antlr.which', return_value=None)

    java_path = command._find_java()
    assert java_path is None


def test_build_antlr_find_java_no_java_home(mocker):
    dist = Distribution()
    command = build_antlr(dist)

    mocker.patch.dict('os.environ')
    del environ['JAVA_HOME']
    mocker.patch('antlr_distutils.build_antlr.which', return_value=None)

    java_path = command._find_java()
    assert java_path is None


def test_build_antlr_find_java_on_path(mocker):
    dist = Distribution()
    command = build_antlr(dist)

    mocker.patch.dict('os.environ')
    del environ['JAVA_HOME']
    mocker.patch('antlr_distutils.build_antlr.which', return_value='c:/path/to/java/bin/java.exe')
    mocker.patch.object(build_antlr, '_validate_java', return_value=True)

    java_path = command._find_java()
    assert java_path is not None
