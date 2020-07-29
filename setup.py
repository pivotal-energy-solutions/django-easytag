# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(name='django-easytag',
      version='2.0.1',
      description='A generic class to facilitate the creation of complex template tags.',
      author='Autumn Valenta',
      author_email='steven@pivotal.energy',
      url='https://github.com/tiliv/django-easytag',
      license='Apache License 2.0',
      classifiers=[
           'Environment :: Web Environment',
           'Framework :: Django',
           'Intended Audience :: Developers',
           'Operating System :: OS Independent',
           'Programming Language :: Python',
           'Topic :: Software Development',
           'License :: OSI Approved :: Apache Software License',
      ],
      py_modules=['easytag'],
      requires=['django (>=1.2)'],
)
