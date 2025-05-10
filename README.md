[![Upload Python Package](https://github.com/mmaleki92/agri/actions/workflows/python-publish.yml/badge.svg)](https://github.com/mmaleki92/agri/actions/workflows/python-publish.yml)

# Anywhere GitHub repository import (Agri)

Happen to you that as a researcher, machine learning practitioner, you run multiple versions of your code in different places? like colab, kaggle, your computer. I had the same problem, so I created this package to help me, and maybe us, to overcome this problem by downloading the repository from GitHub (for private you need to provide a token), and work with it. Then if you want to change something, do it on your computer and push it, then update it in the code.

# Have an idea?
raise an ISSUE.

# Import the package
import agri


```python
agri.authenticate("__token__")

my_repo = agri.import_repo("mmaleki92/test_repo")

print(agri.get_repo_structure("test_repo"))

```
Happy researching.
