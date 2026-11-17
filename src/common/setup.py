#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='common',
    version='0.0.1',
    description='engineering-agents common code',
    license='MIT',
    packages=find_packages(exclude=['tests.*', 'tests']),
    keywords="engineering-agents service",
    python_requires='>=3.14',
    include_package_data=True,
    # boto3 is left out on purpose. The front door uses the copy in the Lambda
    # runtime, to stay small; a function that needs its own lists it.
    install_requires=[
        'aws_lambda_powertools',
    ],
    classifiers=[
        'Environment :: Console',
        'Environment :: Other Environment',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.14',
    ]
)
