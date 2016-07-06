from distutils.dist import Distribution
from os import chdir, environ, path
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from antlr_distutils.build_antlr import AntlrGrammar, build_antlr


@pytest.fixture(scope="module", autouse=True)
def ch_resources_dir():
    localdir = path.dirname(__file__)
    chdir(path.join(localdir, 'resources'))


class TestAntlrGrammar:
    def test_read_with_imports(self):
        grammar = AntlrGrammar(Path('SomeGrammar.g4'))
        imports = set(grammar.read_imports())

        assert len(imports) == 2
        assert {'CommonTerminals', 'SharedRules'} == imports

    def test_read_without_imports(self):
        grammar = AntlrGrammar(Path('CommonTerminals.g4'))
        imports = grammar.read_imports()

        assert not imports

    def test_read_nonexistent_file(self, capsys):
        grammar = AntlrGrammar(Path('FooBar.g4'))
        imports = grammar.read_imports()

        # check if error was logged
        _, err = capsys.readouterr()
        assert 'FooBar.g4' in err
        assert not imports


class TestBuildAntlr:
    def test_find_java_valid_java_home(self, mocker):
        dist = Distribution()
        command = build_antlr(dist)

        mocker.patch.dict('os.environ', {'JAVA_HOME': 'c:/path/to/java'})
        mocker.patch('antlr_distutils.build_antlr.which', return_value='c:/path/to/java/bin/java.exe')
        mocker.patch.object(build_antlr, '_validate_java', return_value=True)

        java_path = command._find_java()
        assert java_path == Path('c:/path/to/java/bin/java.exe')

    def test_find_java_invalid_java_home(self, mocker):
        dist = Distribution()
        command = build_antlr(dist)

        mocker.patch.dict('os.environ', {'JAVA_HOME': 'c:/path/to/java'})
        mocker.patch('antlr_distutils.build_antlr.which', return_value=None)

        java_path = command._find_java()
        assert java_path is None

    def test_find_java_no_java_home(self, mocker):
        dist = Distribution()
        command = build_antlr(dist)

        mocker.patch.dict('os.environ')
        del environ['JAVA_HOME']
        mocker.patch('antlr_distutils.build_antlr.which', return_value=None)

        java_path = command._find_java()
        assert java_path is None

    def test_find_java_on_path(self, mocker):
        dist = Distribution()
        command = build_antlr(dist)

        mocker.patch.dict('os.environ')
        del environ['JAVA_HOME']
        mocker.patch('antlr_distutils.build_antlr.which', return_value='c:/path/to/java/bin/java.exe')
        mocker.patch.object(build_antlr, '_validate_java', return_value=True)

        java_path = command._find_java()
        assert java_path is not None

    test_ids_validate_java = ['valid', 'invalid', 'deprecated', 'corrupt']

    test_data_validate_java = [
        (CompletedProcess(['java.exe', '-version'], 0, stdout="""
java version "1.8.0_92"
Java(TM) SE Runtime Environment (build 1.8.0_92-b14)
Java HotSpot(TM) 64-Bit Server VM (build 25.92-b14, mixed mode)
"""), True),
        (CompletedProcess(['java.exe', '-version'], 0, stdout="""
java version "1.4.0"
Java(TM) 2 Runtime Environment, Standard Edition (build 1.4.0-b03)
Java HotSpot(TM) 64-Bit Server VM (build 1.4.0-b03, mixed mode)
"""), False),
        (CompletedProcess(['java.exe', '-version'], 0, stdout="""
java version "1.5.0_22"
Java(TM) 2 Runtime Environment, Standard Edition (build 1.5.0_22-b03)
Java HotSpot(TM) 64-Bit Server VM (build 1.5.0_22-b03, mixed mode)
"""), False),
        (CompletedProcess(['java.exe', '-version'], 1, stdout=''), False)
    ]

    @pytest.mark.parametrize('result, expected', test_data_validate_java, ids=test_ids_validate_java)
    def test_validate_java(self, mocker, result, expected):
        dist = Distribution()
        command = build_antlr(dist)

        mocker.patch('antlr_distutils.build_antlr.run', return_value=result)

        assert command._validate_java('java.exe') == expected
