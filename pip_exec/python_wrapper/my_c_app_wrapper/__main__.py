import sys
import os
import subprocess
import shutil
import importlib.resources

def find_executable():
    """Find the bundled C executable."""
    # Use importlib.resources for robust path finding within the installed package
    try:
        # In Python 3.9+ use files() API correctly - don't use context manager
        exe_name = "my_c_app_exec" + (".exe" if sys.platform == "win32" else "")
        # Assuming the binary is in a 'bin' subdirectory within the package
        pkg_dir = importlib.resources.files("my_c_app_wrapper")
        exe_path = pkg_dir / "bin" / exe_name
        if exe_path.is_file():
            return str(exe_path) # Return path as string
    except (AttributeError, ImportError):
        # Fallback for older Python or if files() API fails
        # This is less robust than importlib.resources.files
        try:
            # Find the package path somewhat manually
            import my_c_app_wrapper
            base_path = os.path.dirname(my_c_app_wrapper.__file__)
            exe_name = "my_c_app_exec" + (".exe" if sys.platform == "win32" else "")
            exe_path = os.path.join(base_path, "bin", exe_name)
            if os.path.isfile(exe_path):
                return exe_path
        except Exception as e:
            pass # Handle potential errors finding the path
    
    # Another fallback method using __file__ directly
    try:
        import my_c_app_wrapper
        base_path = os.path.dirname(os.path.abspath(my_c_app_wrapper.__file__))
        exe_name = "my_c_app_exec" + (".exe" if sys.platform == "win32" else "")
        exe_path = os.path.join(base_path, "bin", exe_name)
        if os.path.isfile(exe_path):
            return exe_path
    except Exception as e:
        pass
        
    raise FileNotFoundError("Could not find the bundled C executable.")


def main():
    try:
        executable_path = find_executable()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:] # Get arguments passed to the Python script
    
    # Directly execute the C application
    cmd = [executable_path] + args
    
    print(f"Executing: {' '.join(cmd)}")
    try:
        # Use subprocess.run for better control and error handling
        result = subprocess.run(cmd, check=False) # check=False to handle non-zero exit codes manually
        # Exit with the same code as the C executable
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Failed to execute command: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

