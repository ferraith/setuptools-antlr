"""Setup script for antlr-distutils."""

# need to guard script here due to reentrance while testing multiprocessing:
if __name__ == '__main__':
    from setuptools import setup, find_packages
    from sys import version_info, argv

    if version_info < (3, 5):
        print('This Python version is not supported, minimal version 3.5 is required.')
        exit(1)

    needs_pytest = {'pytest', 'test', 'ptr'}.intersection(argv)
    pytest_runner_opt = ['pytest-runner>=2.0,<3dev'] if needs_pytest else []

    setup(
            name='antlr-distutils',
            version='0.0.1',
            packages=find_packages(),
            package_data={'antlr_distutils': ['lib/antlr-4.5.3-complete.jar', 'lib/LICENSE.txt']},
            tests_require=[
                'pytest'
            ],
            setup_requires=pytest_runner_opt,
            url='https://github.com/ferraith/antlr-distutils',
            license='',
            author='Andreas Schmidl',
            author_email='Andreas.Schmidl@gmail.com',
            description='A distutils extension for generating ANTLR based parsers.',
            keywords='antlr distutils dsl',
            classifiers=[
                'Development Status :: 2 - Alpha',
                'Intended Audience :: Developers',
                'Topic :: Software Development',
                'License :: Other/Proprietary License',
                'Programming Language :: Python :: 3.5',
            ],
    )
