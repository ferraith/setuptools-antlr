import os
import pathlib
import subprocess
import unittest.mock

import pytest

from setuptools_antlr.util import camel_to_snake_case, find_java, validate_java


def test_camel_to_snake_case():
    assert 'ab' == camel_to_snake_case('Ab')
    assert 'ab_cd' == camel_to_snake_case('AbCd')
    assert 'aa_bb_cc' == camel_to_snake_case('AaBbCc')
    assert 'ab0_cd1' == camel_to_snake_case('Ab0Cd1')
    assert 'abcd' == camel_to_snake_case('Abcd')
    assert 'ab' == camel_to_snake_case('AB')
    assert 'ab0' == camel_to_snake_case('AB0')


@unittest.mock.patch('shutil.which')
@unittest.mock.patch('setuptools_antlr.util.validate_java')
def test_find_java_valid_java_home(mock_validate_java, mock_which):
    with unittest.mock.patch.dict('os.environ', {'JAVA_HOME': 'c:/path/to/java'}):
        mock_which.return_value = 'c:/path/to/java/bin/java.exe'
        mock_validate_java.return_value = True

        java_path = find_java('1.7.0')

    assert java_path == pathlib.Path('c:/path/to/java/bin/java.exe')


@unittest.mock.patch('shutil.which')
def test_find_java_invalid_java_home(mock_which):
    with unittest.mock.patch.dict('os.environ', {'JAVA_HOME': 'c:/path/to/java'}):
        mock_which.return_value = None

        java_path = find_java('1.7.0')

    assert java_path is None


@unittest.mock.patch('shutil.which')
def test_find_java_no_java_home(mock_which):
    with unittest.mock.patch.dict('os.environ'):
        del os.environ['JAVA_HOME']
        mock_which.return_value = None

        java_path = find_java('1.7.0')

    assert java_path is None


@unittest.mock.patch('shutil.which')
@unittest.mock.patch('setuptools_antlr.util.validate_java')
def test_find_java_on_path(mock_validate_java, mock_which):
    with unittest.mock.patch.dict('os.environ'):
        del os.environ['JAVA_HOME']
        mock_which.return_value = 'c:/path/to/java/bin/java.exe'
        mock_validate_java.return_value = True

        java_path = find_java('1.7.0')

    assert java_path is not None

test_ids_validate_java = ['valid', 'invalid', 'deprecated', 'corrupt']

test_data_validate_java = [
    (subprocess.CompletedProcess(['java.exe', '-version'], 0, stdout="""
java version "1.8.0_92"
Java(TM) SE Runtime Environment (build 1.8.0_92-b14)
Java HotSpot(TM) 64-Bit Server VM (build 25.92-b14, mixed mode)
"""), True),
        (subprocess.CompletedProcess(['java.exe', '-version'], 0, stdout="""
java version "1.4.0"
Java(TM) 2 Runtime Environment, Standard Edition (build 1.4.0-b03)
Java HotSpot(TM) 64-Bit Server VM (build 1.4.0-b03, mixed mode)
"""), False),
        (subprocess.CompletedProcess(['java.exe', '-version'], 0, stdout="""
java version "1.5.0_22"
Java(TM) 2 Runtime Environment, Standard Edition (build 1.5.0_22-b03)
Java HotSpot(TM) 64-Bit Server VM (build 1.5.0_22-b03, mixed mode)
"""), False),
        (subprocess.CompletedProcess(['java.exe', '-version'], 1, stdout=''), False)
]


@pytest.mark.parametrize('result, expected', test_data_validate_java,
                         ids=test_ids_validate_java)
@unittest.mock.patch('subprocess.run')
def test_validate_java(mock_run, result, expected):
    mock_run.return_value = result

    assert validate_java('java.exe', '1.7.0') == expected
