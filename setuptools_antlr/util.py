"""Utilities required by 'antlr' setuptools command ."""
import os.path
import pathlib
import shutil
import subprocess
import distutils.version
import re


def camel_to_snake_case(s):
    """Converts a camel cased to a snake cased string.

    :param s: a camel cased string
    :return: a snake cased string
    """
    snake_cased = re.sub('([a-z0-9])([A-Z])', r'\1_\2', re.sub('(.)([A-Z][a-z]+)', r'\1_\2',
                                                               s)).lower()
    return snake_cased.replace('__', '_')


def validate_java(executable: str, min_java_version: str) -> bool:
    """Validates a Java Runtime Environment (JRE) if it fulfills minimum acceptable version.

    :param executable: Java executable of JRE
    :param min_java_version: minimum acceptable version of Java
    :return: flag whether JRE is at minimum required version
    """
    result = subprocess.run([executable, '-version'], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, universal_newlines=True)

    if result.returncode == 0:
        version_regex = re.compile('"([1-9]\d*(?:(\.0)|(\.[1-9]\d*))*(?:_\d+)?)"')
        version_match = version_regex.search(result.stdout)

        if version_match:
            # create normalized versions containing only valid chars
            validated_version = distutils.version.LooseVersion(version_match.group(1).
                                                               replace('_', '.'))
            min_version = distutils.version.LooseVersion(min_java_version.replace('_', '.'))

            return validated_version >= min_version

    return False


def find_java(min_java_version: str) -> pathlib.Path:
    """Searches for a working Java Runtime Environment (JRE) set in JAVA_HOME or PATH
    environment variables. A JRE located in JAVA_HOME will be preferred.

    :param min_java_version: minimum acceptable version of Java
    :return: a path to a working JRE or None if no JRE was found
    """
    # first check if a working Java is set in JAVA_HOME
    if 'JAVA_HOME' in os.environ:
        java_bin_dir = os.path.join(os.environ['JAVA_HOME'], 'bin')
        java_exe = shutil.which('java', path=java_bin_dir)
        if java_exe and validate_java(java_exe, min_java_version):
            return pathlib.Path(java_exe)

    # if Java wasn't found in JAVA_HOME fallback to PATH
    java_exe = shutil.which('java', path=None)
    if java_exe and validate_java(java_exe, min_java_version):
        return pathlib.Path(java_exe)

    # java wasn't found on the system
    return None
