from setuptools import setup, find_packages

setup(
    name="pcapi",
    version="1.4",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,

    package_data={
        'pcapi': ['data/*',],
    },

    install_requires=['Wand==0.3.8',
                      'beautifulsoup4==4.1.3',
                      'bottle==0.11.4',
                      'dropbox==1.5.1',
                      'html5lib==0.95',
                      'lxml==3.1.2',
                      'simplekml==1.2.1',
                      'threadpool==1.2.7',
                      'WebTest==2.0.4',
                      'pysqlite==2.6.3'],

    zip_safe=True,
    entry_points={
        'console_scripts': [
            'pcapi = pcapi.server:runserver',
            'pcapi_upgrade = pcapi.utils.pcapi_upgrade:upgrade_all_data'
        ]
    }
)
