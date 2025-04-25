"""
Setup script for my_c_app_wrapper package.
This hooks the custom build process into setuptools.
"""
import os
import sys
from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

sys.path.insert(0, os.path.abspath('.'))
try:
    from my_c_app_wrapper.build_helpers import build_c_project
except ImportError:
    # If build_helpers is not yet available, create a minimal version here
    def build_c_project(package_dir):
        print("ERROR: Could not import build_helpers.py!")
        print("This shouldn't happen if you're running setup.py after checking out the repo.")
        sys.exit(1)


class build_py(_build_py):
    """Custom build command to compile C code before Python build."""
    def run(self):
        """Run the build process."""
        # First, ensure Python package build structure exists
        self.run_command('egg_info')
        
        # Build the C project
        print(f"--- Running custom C build for target directory: {self.build_lib} ---")
        build_c_project(self.build_lib)
        print("--- Custom C build finished ---")
        
        # Run the standard Python build process
        super().run()


# Hook the custom build command
setup(
    cmdclass={
        'build_py': build_py,
    },
)