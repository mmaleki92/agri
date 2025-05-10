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
# Simple Guide

A simple guide to using the repository browser to work with GitHub repositories.

## Table of Contents
- [Quick Start](#quick-start)
- [Basic Operations](#basic-operations)
- [Working with Files](#working-with-files)
- [Committing Changes](#committing-changes)

## Quick Start

Here's a simple example to get started:

```python
# Import the library
import agri

# Authenticate with your GitHub token
agri.authenticate("your_github_token")

# Import a repository
my_repo = agri.import_repo("username/repo_name")

# Access a Python file or module
my_module = my_repo.folder.module_name  # Automatically looks for module_name.py

# Use functions from the module
result = my_module.some_function()
```

## Basic Operations

### Importing a Repository

```python
# Import a repository
my_repo = agri.import_repo("username/repo_name")

# Import a specific branch
dev_branch = agri.import_repo("username/repo_name", branch="development")
```

### Viewing Repository Structure

```python
# Show repository structure during import
my_repo = agri.import_repo("username/repo_name", show_structure=True)

# View structure of an already imported repository
structure = agri.get_repo_structure("username/repo_name")
print(structure)

# List all imported repositories
repos = agri.list_imported_repos()
print(repos)
```

### Exploring Repository Contents

```python
# List top-level folders and files
print(dir(my_repo))

# Navigate through directories
print(dir(my_repo.src))
print(dir(my_repo.src.utils))
```

### Updating a Repository

```python
# Update to get latest changes
updated_repo = agri.update_repo("username/repo_name")
```

## Working with Files

### Accessing Python Files

Files are lazily loaded - they're only executed when you access them:

```python
# Access a module (this will execute the Python file)
helper = my_repo.src.utils.helper  # Automatically finds helper.py

# Use functions or classes from the module
result = helper.process_data(my_data)
```

### Reading File Contents Without Execution

```python
import os

# Get file path without executing code
file_path = os.path.join(my_repo.__path__, "README.md")

# Read content
with open(file_path, 'r') as f:
    content = f.read()
    print(content)
```

## Committing Changes

### Creating a New File

```python
# Create and commit a new file
agri.create_file_and_commit(
    "username/repo_name",
    file_content="print('Hello, world!')",
    repo_file_path="examples/hello.py",
    message="Add hello world example"
)
```

### Committing Local Files

```python
# Commit a single file
agri.commit_files(
    "username/repo_name",
    local_source="/path/to/local/file.py",
    repo_target="src/utils/file.py",
    message="Add utility file"
)

# Commit multiple files
agri.commit_files(
    "username/repo_name",
    local_source={
        "/path/to/file1.py": "src/file1.py",
        "/path/to/file2.py": "src/file2.py"
    },
    message="Add multiple files"
)
```

### Deleting Files

```python
# Delete a file or directory
agri.delete_files_and_commit(
    "username/repo_name",
    repo_file_paths="old_file.py",
    message="Remove old file"
)

# Delete multiple files/directories
agri.delete_files_and_commit(
    "username/repo_name",
    repo_file_paths=["file1.py", "old_folder/"],
    message="Remove unused files"
)
```

## Example Workflow

Here's a complete example workflow:

```python
import agri

# Step 1: Authenticate
agri.authenticate("your_github_token")

# Step 2: Import a repository
my_repo = agri.import_repo("username/my-project")

# Step 3: Navigate and use repository contents
config = my_repo.src.config  # Access config.py file
settings = config.DEFAULT_SETTINGS  # Get a variable from the file

# Step 4: Make changes and commit them
agri.create_file_and_commit(
    "username/my-project",
    file_content=f"""
# Updated configuration
DEFAULT_SETTINGS = {settings}
DEBUG = True
""",
    repo_file_path="src/config.py",
    message="Update configuration settings"
)
```

That's it! This quick guide covers the basics of working with repositories, accessing files, and committing changes.