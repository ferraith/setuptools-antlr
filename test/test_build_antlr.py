from setuptools.dist import Distribution
from os import chdir, environ, path
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from setuptools_antlr.build_antlr import AntlrGrammar, build_antlr


@pytest.fixture(scope='module', autouse=True)
def ch_resources_dir(request):
    chdir('.')
    init_dir = Path.cwd()
    local_dir = path.dirname(__file__)
    chdir(path.join(local_dir, 'resources'))

    def fin():
        chdir(str(init_dir))
    request.addfinalizer(fin)


class TestAntlrGrammar:
    def test_read_with_imports(self):
        grammar = AntlrGrammar(Path('distributed', 'SomeGrammar.g4'))
        imports = set(grammar.read_imports())

        assert len(imports) == 2
        assert {'CommonTerminals', 'SharedRules'} == imports

    def test_read_without_imports(self):
        grammar = AntlrGrammar(Path('distributed', 'CommonTerminals.g4'))
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
    @pytest.fixture(autouse=True)
    def command(self):
        dist = Distribution()
        return build_antlr(dist)

    def test_find_java_valid_java_home(self, mocker, command):
        mocker.patch.dict('os.environ', {'JAVA_HOME': 'c:/path/to/java'})
        mocker.patch('setuptools_antlr.build_antlr.which',
                     return_value='c:/path/to/java/bin/java.exe')
        mocker.patch.object(build_antlr, '_validate_java', return_value=True)

        java_path = command._find_java()
        assert java_path == Path('c:/path/to/java/bin/java.exe')

    def test_find_java_invalid_java_home(self, mocker, command):
        mocker.patch.dict('os.environ', {'JAVA_HOME': 'c:/path/to/java'})
        mocker.patch('setuptools_antlr.build_antlr.which', return_value=None)

        java_path = command._find_java()
        assert java_path is None

    def test_find_java_no_java_home(self, mocker, command):
        mocker.patch.dict('os.environ')
        del environ['JAVA_HOME']
        mocker.patch('setuptools_antlr.build_antlr.which', return_value=None)

        java_path = command._find_java()
        assert java_path is None

    def test_find_java_on_path(self, mocker, command):
        mocker.patch.dict('os.environ')
        del environ['JAVA_HOME']
        mocker.patch('setuptools_antlr.build_antlr.which',
                     return_value='c:/path/to/java/bin/java.exe')
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

    @pytest.mark.parametrize('result, expected', test_data_validate_java,
                             ids=test_ids_validate_java)
    def test_validate_java(self, mocker, command, result, expected):
        mocker.patch('setuptools_antlr.build_antlr.run', return_value=result)

        assert command._validate_java('java.exe') == expected

    test_ids_find_antlr = ['single', 'multiple', 'none', 'invalid']

    test_data_find_antlr = [
        ({'antlr-4.5.3-complete.jar'}, 'antlr-4.5.3-complete.jar'),
        ({'antlr-0.1.1-complete.jar', 'antlr-3.0-complete.jar', 'antlr-4.5.2-complete.jar',
          'antlr-4.5.3-complete.jar'},
         'antlr-4.5.3-complete.jar'),
        ({}, None),
        ({'antlr-runtime-4.5.3.jar'}, None)
    ]

    @pytest.mark.parametrize('available_antlr_jars, expected_antlr_jar', test_data_find_antlr,
                             ids=test_ids_find_antlr)
    def test_find_antlr(self, mocker, tmpdir, command, available_antlr_jars, expected_antlr_jar):
        ext_lib_dir = tmpdir.mkdir('lib')
        for jar in available_antlr_jars:
            antlr_jar = ext_lib_dir.join(jar)
            antlr_jar.write('dummy')

        mocker.patch.object(build_antlr, '_EXT_LIB_DIR', str(ext_lib_dir))

        found_antlr_jar = command._find_antlr()
        assert found_antlr_jar == (Path(str(ext_lib_dir), expected_antlr_jar) if expected_antlr_jar
                                   else None)

    def test_find_grammars_empty(self, tmpdir, command):
        dsl_dir = tmpdir.mkdir('dsl')
        g = command._find_grammars(Path(str(dsl_dir)))

        assert len(g) == 0

    def test_find_grammars_standalone(self, command):
        g = command._find_grammars(Path('standalone'))

        assert len(g) == 1
        assert g[0].name == 'SomeGrammar'

    def test_find_grammars_distributed(self, command):
        g = command._find_grammars(Path('distributed'))

        assert len(g) == 1
        assert g[0].name == 'SomeGrammar'
        d = g[0].dependencies
        assert len(d) == 2
        assert d[0].name == 'CommonTerminals'
        assert d[1].name == 'SharedRules'
        dd = g[0].dependencies[0].dependencies
        assert len(dd) == 0
        dd = g[0].dependencies[1].dependencies
        assert len(dd) == 1
        assert dd[0].name == 'CommonTerminals'

    def test_find_grammars_incomplete(self, command):
        g = command._find_grammars(Path('incomplete'))

        assert len(g) == 0

    def test_finalize_options_default(self, command):
        command.finalize_options()

        assert command.listener is True
        assert command.visitor is True

    def test_finalize_options_configured(self, command):
        command.listener = False
        command.visitor = False

        command.finalize_options()

        assert command.listener is False
        assert command.visitor is False
