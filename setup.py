# -*- coding: utf-8 -*-
import os
from setuptools import find_packages, setup


INSTALL_REQUIRES = [
    'coreapi>=2.0.9,<2.1',
    'django-bootstrap-breadcrumbs>=0.8.1,<0.9',
    'django-bootstrap-pagination>=1.6.2,<1.7',
    'django-braces>=1.10,<1.12',
    'django-chunked-upload>=1.1.1,<1.2',
    'django-compressor>=2.1,<2.2',
    'django-constance[database]>=1.3.3,<2',
    'django-geoposition>=0.3,<0.4',
    'django-rq>=0.9.4,<1',
    'django_select2>=5.8.8,<5.11',
    'django-widget-tweaks>=1.4.1,<1.5',
    'pytz>=2016.6.1',
    'serpy>=0.1.1,<1.2',
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
