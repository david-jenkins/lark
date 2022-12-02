# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))


# -- Project information -----------------------------------------------------

project = 'lark'
copyright = '2022, David Jenkins'
author = 'David Jenkins'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
    'autoapi.extension']

autosummary_generate = True

autoapi_root = "autoapi"
autoapi_dirs = ["../../lark"]
autoapi_type = 'python'
autoapi_template_dir = '_autoapi_templates'
autoapi_add_toctree_entry = False
autoapi_keep_files = True
autoapi_generate_api_docs = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'lark/darc']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['../../system/centos-cfg/lark.png']

modindex_common_prefix = ["lark."]

html_theme_options = {
    'logo': 'lark.png',
    'github_user': 'david-jenkins',
    'github_repo': 'lark',
    'fixed_sidebar': True,
    'description': "Some Python code for the DARC RTC"
}

# def run_apidoc(_):
#     from sphinx.ext.apidoc import main
#     from pathlib import Path
#     cur_dir = Path(__file__).parent.absolute()
#     module = cur_dir.parent.parent/"lark"
#     output_path = cur_dir/"automodules"
#     exclude_path = module/"darc"
#     main(['-f', '-d', '2', '-e', '-M', '-o', str(output_path), str(module), str(exclude_path)])

# def setup(app):
#     app.connect('builder-inited', run_apidoc)
