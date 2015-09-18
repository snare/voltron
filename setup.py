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
    packages=find_packages(exclude=['tests', 'examples']),
    install_requires = ['rl', 'scruffington', 'flask', 'cherrypy', 'blessed', 'pygments'],
    package_data = {'voltron': ['config/*']},
    entry_points = {
        'console_scripts': ['voltron = voltron:main']
    },
    zip_safe = False
)
