from setuptools import setup, find_packages

setup(
    name = "voltron",
    version = "0.1",
    author = "snare",
    author_email = "snare@ho.ax",
    description = ("A UI for GDB & LLDB"),
    license = "Buy snare a beer",
    keywords = "voltron gdb lldb",
    url = "https://github.com/snarez/voltron",
    packages=find_packages(),
    install_requires = ['rl', 'scruffy', 'flask', 'cherrypy', 'blessed'],
    data_files=['dbgentry.py'],
    package_data = {'voltron': ['config/*']},
    install_package_data = True,
    entry_points = {
        'console_scripts': ['voltron = voltron:main']
    },
    zip_safe = False,
    dependency_links = ["https://github.com/snarez/scruffy/tarball/v0.2.1#egg=scruffy"]
)
