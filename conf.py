"""Sphinx configuration file."""

extensions = ["myst_parser", "sphinx_external_toc"]
exclude_patterns = [".github", ".tox", ".vscode", "_build"]
external_toc_exclude_missing = True
html_theme = "furo"
