from setuptools.command.build_py import build_py as _build_py
from setuptools import setup 
import os
import sys
try:
    from my_c_app_wrapper.build_helpers import build_c_project
except ImportError:
    sys.path.insert(0, os.path.abspath('.'))
    from my_c_app_wrapper.build_helpers import build_c_project


class build_py(_build_py):
    def run(self):
        package_build_dir = self.build_lib
        print(f"--- Running custom C build for target directory: {package_build_dir} ---")
        build_c_project(package_build_dir)
        print("--- Custom C build finished ---")
        super().run()

if __name__ == "__main__":
     setup(
         cmdclass={'build_py': build_py}
     )
