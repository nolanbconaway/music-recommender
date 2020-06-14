from setuptools import find_packages, setup

setup(
    name="app",
    version="0.0.1",
    package_dir={"": "app"},
    packages=find_packages("app"),
    package_data={"app": ["templates/*"]},
)
