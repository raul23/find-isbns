"""setup.py file for the ``find_isbns`` package.
"""
import fnmatch
import os
import sys
from setuptools import find_packages, setup
from setuptools.command.build_py import build_py as build_py_orig

from find_isbns import __version__, __test_version__

if sys.version_info < (3, 7):
    raise RuntimeError("""
    find_isbns v0.1.0+ supports Python 3.7 and above. 
    """)

excluded = []
    

# IMPORTANT: bdist_wheel behaves differently to sdist
# - MANIFEST.in works for source distributions, but it's ignored for wheels,
#   See https://bit.ly/3s2Kt3p
# - "bdist_wheel would always include stuff that I'd manage to exclude from the sdist"
#   See https://bit.ly/3t7SsO4
# Code reference: https://stackoverflow.com/a/56044136/14664104
class build_py(build_py_orig):
    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        return [
            (pkg, mod, file)
            for (pkg, mod, file) in modules
            if not any(fnmatch.fnmatchcase(file, pat=pattern) for pattern in excluded)
        ]


# Choose the correct version based on script's arg
if len(sys.argv) > 1 and sys.argv[1] == "testing":
    VERSION = __test_version__
    # Remove "testing" from args so setup doesn't process "testing" as a cmd
    sys.argv.remove("testing")
else:
    VERSION = __version__

# Directory of this file
dirpath = os.path.abspath(os.path.dirname(__file__))

# The text of the README file
with open(os.path.join(dirpath, "README.rst"), encoding="utf-8") as f:
    README = f.read()

# The text of the requirements.txt file
# TODO: empty for now
with open(os.path.join(dirpath, "requirements.txt")) as f:
    REQUIREMENTS = f.read().splitlines()


setup(name='find-isbns',
      version=VERSION,
      description='''Find ISBNs from ebooks (pdf, djvu, epub).''',
      long_description=README,
      long_description_content_type='text/x-rst',
      classifiers=[
        'Development Status :: 3 - Alpha',  # TODO: change version to beta or stable
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities'
      ],
      keywords='calibre convert djvu epub isbn ocr pdf script',
      url='https://github.com/raul23/find-isbns',
      author='Raul C.',
      author_email='rchfe23@gmail.com',
      license='MIT',
      python_requires='>=3.7',
      # packages=find_packages(exclude=['tests']),
      cmdclass={'build_py': build_py},
      include_package_data=True,
      install_requires=REQUIREMENTS,
      entry_points={
        'console_scripts': ['find_isbns=find_isbns.scripts.find_isbns:main']
      },
      project_urls={  # Optional
          'Bug Reports': 'https://github.com/raul23/find-isbns/issues',
          'Source': 'https://github.com/raul23/find-isbns',
      },
      zip_safe=False)
