from setuptools import setup, find_packages

setup(
    name="agri",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "gitpython>=3.1.0",
        "keyring>=23.0.0",
    ],
    author="Your Name",
    author_email="maleki.morteza92@gmail.com",
    description="Import Python modules directly from GitHub repositories",
    keywords="github, import, repository, private",
    url="https://github.com/mmaleki92/agri",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
)