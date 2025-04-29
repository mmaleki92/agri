[![Upload Python Package](https://github.com/mmaleki92/pyising/actions/workflows/python-publish.yml/badge.svg)](https://github.com/mmaleki92/agri/actions/workflows/python-publish.yml)

# Anywhere github repository import (Agri)

Happend to you that as a resercher, machine learning practinoiner, run multiple versions of your codes in a different places? like colab, kaggle, your computer. I had the same problem, so I created this package to help me, and maybe us, to overcome this problem by downloading the repository from github (for private you need to provide a token), and work with it. then if you wnat to change something, do it in your computer and push it, then update it to in the code.

# have an idea? face an error?
raise an ISSUE.

# Import the package
import agri


```python
agri.authenticate("__token__")

my_repo = agri.import_repo("mmaleki92/test_repo")

print(agri.get_repo_structure("test_repo"))

```
happy researching.