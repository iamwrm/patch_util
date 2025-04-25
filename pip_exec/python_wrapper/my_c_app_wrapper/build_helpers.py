import os
import sys
import logging
import subprocess

# Update logging configuration to use environment variable
log_level = os.environ.get('BUILD_LOG_LEVEL', 'INFO')
numeric_level = getattr(logging, log_level.upper(), logging.INFO)
logging.basicConfig(
    level=numeric_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# --- Constants ---
ZIG_VERSION = "0.14.0" # Example version, choose a recent stable one
CMAKE_VERSION = "3.27.7" # Example version
BUILD_DIR = "build_c"
INSTALL_DIR = os.path.abspath("c_install") # Absolute path for CMake install prefix
SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "build_c_app.sh"))

# --- Build Function ---
def build_c_project(package_dir):
    """Builds the C project by calling the bash script."""
    log.info("Starting C project build process...")
    log.debug(f"Package directory: {package_dir}")
    
    # Make sure the script is executable
    if not os.access(SCRIPT_PATH, os.X_OK):
        log.debug(f"Making script executable: {SCRIPT_PATH}")
        os.chmod(SCRIPT_PATH, 0o755)
    
    # Target directory for the final executable
    target_dir = os.path.join(package_dir, "my_c_app_wrapper", "bin")
    
    # Prepare command with arguments
    cmd = [
        SCRIPT_PATH,
        "--zig-version", ZIG_VERSION,
        "--cmake-version", CMAKE_VERSION,
        "--build-dir", BUILD_DIR,
        "--install-dir", INSTALL_DIR,
        "--source-dir", os.path.abspath("../src"),
        "--target-dir", target_dir,
    ]
    
    # Add verbose flag if log level is DEBUG
    if log_level.upper() == "DEBUG":
        cmd.append("--verbose")
    
    log.debug(f"Running command: {' '.join(cmd)}")
    
    try:
        # Run the script
        env = os.environ.copy()
        # Use subprocess.run to capture output
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True, # Capture stdout and stderr
            text=True # Decode output as text
        )
        
        # Log stdout/stderr regardless of success if debugging
        if result.stdout:
            log.debug("Build script stdout:\n%s", result.stdout)
        if result.stderr:
            log.debug("Build script stderr:\n%s", result.stderr)

        # Check return code manually
        if result.returncode != 0:
            log.error(f"Build script failed with code {result.returncode}")
            # Print captured output on error
            if result.stdout:
                log.error("Build script stdout:\n%s", result.stdout)
            if result.stderr:
                log.error("Build script stderr:\n%s", result.stderr)
            # Raise an exception to signal failure
            raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
        
        log.info("C project build process finished successfully.")
    except Exception as e:
        # Catch any other potential exceptions during subprocess handling
        log.error(f"An unexpected error occurred during the build process: {e}")
        raise
