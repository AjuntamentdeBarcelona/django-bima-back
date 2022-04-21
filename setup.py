# -*- coding: utf-8 -*-
import os
from setuptools import find_packages, setup


INSTALL_REQUIRES = [
    'coreapi>=2.0.9,<2.1',
    'django-bootstrap-breadcrumbs==0.9.1',
    'django-bootstrap-pagination==1.7.1',
    'django-braces==1.14.0',
    'django-chunked-upload==2.0.0',
    'django-compressor==2.4',
    'django-constance[database]==2.8.0',
    'django-geoposition-2@git+https://git@github.com/pramon-apsl/django-geoposition.git',
    'django-rq==2.4.0',
    'django_select2==7.6.1',
    'django-widget-tweaks>=1.4.1,<1.5',
    'pytz==2021.1',
    'serpy==0.3.1',
]


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


setup(
    name='django-bima-back',
    version='0.8.0',
    packages=find_packages(exclude=['tests_project.*', 'tests_project']),
    include_package_data=True,
    license='GPLv3',
    description='Django backoffice app to manage digital assets.',
    long_description=README,
    install_requires=INSTALL_REQUIRES,
    author='Advanced Programming Solutions SL (APSL)',
    author_email='info@apsl.net',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
