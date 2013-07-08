# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(name='django-datatable-view',
      version='1.0',
      description='A generic class to facilitate the creation of complex template tags.',
      author='Tim Valenta',
      author_email='tim.valenta@thesimpler.net',
      url='https://github.com/tiliv/django-easytag',
      license='',
      classifiers=[
           'Environment :: Web Environment',
           'Framework :: Django',
           'Intended Audience :: Developers',
           'Operating System :: OS Independent',
           'Programming Language :: Python',
           'Topic :: Software Development',
      ],
      package_data={'eastytag': ['easytag.py']},
      include_package_data=True,
      requires=['django (>=1.2)'],
)
