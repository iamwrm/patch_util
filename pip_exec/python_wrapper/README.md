# My C App Python Wrapper

A Python wrapper for a sample C application compiled with Zig.

This directory contains the Python package (`my_c_app_wrapper`) and associated files.
The C source code and the main build script (`build_c_app.sh`) are located in the parent directory.

## Features

- Python package (`my_c_app_wrapper`) that wraps a C executable.
- Uses a build script (`../build_c_app.sh`) located in the parent directory.
- Build script automatically downloads Zig compiler and CMake.
- Build script builds the C application (`../src`) during Python package installation.
- Provides a Python CLI interface (`my_c_app`) to the C executable.
- Caches downloaded tools (Zig, CMake) in the parent `build_c` directory.
- Build script supports partial builds and custom configurations.

## Installation

Navigate to this directory (`python_wrapper`) and install the package directly from source:

```bash
# Ensure you are in the python_wrapper directory
cd python_wrapper

# With pip
pip install .

# Or with uv
uv pip install .
```

This will trigger the build script (`../build_c_app.sh`) to compile the C code located in `../src` and place the executable within the Python package.

## Usage

Once installed, run the application from anywhere:

```bash
my_c_app [arguments]
```

This will execute the packaged C application with the provided arguments.

## Building the C Application Manually

You can manually run the build script located in the parent directory to build the C application without installing the Python package.

From the **project root directory** (the parent of this `python_wrapper` directory):

```bash
./build_c_app.sh [options]
```

### Options

- `--zig-version VERSION`: Set the Zig version (default: 0.14.0)
- `--cmake-version VERSION`: Set the CMake version (default: 3.27.7)
- `--build-dir DIR`: Set the build directory (default: build_c)
- `--install-dir DIR`: Set the C installation directory (default: c_install)
- `--source-dir DIR`: Set the C source directory (default: src)
- `--target-dir DIR`: Explicitly copy the final executable to this directory (otherwise, it stays in `<install-dir>/bin/`)
- `--verbose`: Enable verbose output
- `--step STEPS`: Run specific steps (comma-separated: `zig`, `cmake`, `configure`, `build`, `install`, `copy`, `clean`)

### Build Steps Examples (Run from project root)

- `zig`: Download Zig only (`./build_c_app.sh --step zig`)
- `cmake`: Download CMake only (`./build_c_app.sh --step cmake`)
- `configure`: Configure CMake (`./build_c_app.sh --step configure`)
- `build`: Configure and build (`./build_c_app.sh --step build`)
- `install`: Configure, build, install C artifacts to `c_install` (`./build_c_app.sh --step install`)
- `copy`: Copy executable *if* build/install done previously and `--target-dir` is set.
- `clean`: Remove build artifacts (`./build_c_app.sh --step clean`)

Run multiple steps:

```bash
# Clean, configure, and build C code (run from root)
./build_c_app.sh --step clean,configure,build

# Download tools and configure only (run from root)
./build_c_app.sh --step zig,cmake,configure

# Build and install C artifacts (run from root)
./build_c_app.sh --step install 
# Executable will be in ./c_install/bin/

# Build, install, and copy to a specific location (run from root)
./build_c_app.sh --step install --target-dir ./dist
# Executable will be in ./c_install/bin/ AND ./dist/
```

## Testing the Wrapper

A test script is included in this directory:

```bash
# Ensure you are in the python_wrapper directory
cd python_wrapper
./test.sh
```
This script reinstalls the package and runs the wrapper.

## Project Structure (Relative to project root)

- `src/` - C source code and CMakeLists.txt
- `python_wrapper/` - This directory
  - `my_c_app_wrapper/` - Python package source
  - `pyproject.toml` - Python package definition
  - `README.md` - This file
  - `test.sh` - Test script for the Python wrapper
  - `.venv/` - Virtual environment (created by user or test script)
- `build_c_app.sh` - Main bash script to build the C application
- `build_c/` - C build directory (created by script)
- `c_install/` - C installation directory (created by script) 