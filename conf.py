"""Sphinx configuration file."""

project = html_title = "AiiDA Enhancement Proposals"
author = "The AiiDA team"

extensions = ["myst_parser", "sphinx_external_toc"]
exclude_patterns = [".github", ".tox", ".vscode", "_build"]
external_toc_exclude_missing = True
html_theme = "furo"
suppress_warnings = ["myst.header"]
