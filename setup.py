from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="agri",
    version="0.1.2",
    author="Morteza Maleki",
    author_email="maleki.morteza92@gmail.com",
    description="Anywhere GitHub Repository Importer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mmaleki92/agri",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "gitpython",
        "keyring",
        "tqdm",
    ],
)