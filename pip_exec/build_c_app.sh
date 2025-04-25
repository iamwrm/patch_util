#!/bin/bash
set -e  # Exit on error

# Default values
ZIG_VERSION="0.14.0"
CMAKE_VERSION="3.27.7"
BUILD_DIR="build_c"
INSTALL_DIR="c_install"
SOURCE_DIR="src"
TARGET_DIR=""
VERBOSE=${VERBOSE:-0}
STEPS=()

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --zig-version)
      ZIG_VERSION="$2"
      shift 2
      ;;
    --cmake-version)
      CMAKE_VERSION="$2"
      shift 2
      ;;
    --build-dir)
      BUILD_DIR="$2"
      shift 2
      ;;
    --install-dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --source-dir)
      SOURCE_DIR="$2"
      shift 2
      ;;
    --target-dir)
      TARGET_DIR="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=1
      shift
      ;;
    --step)
      # Split the comma-separated list into an array
      IFS=',' read -r -a STEPS <<< "$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Function to log messages
log() {
  local level=$1
  local message=$2
  if [[ $level == "INFO" || $VERBOSE -eq 1 ]]; then
    echo "[$level] $message"
  fi
}

# Detect platform
detect_platform() {
  SYSTEM=$(uname -s)
  MACHINE=$(uname -m)
  
  log "INFO" "Detected platform: $SYSTEM $MACHINE"
  
  case $SYSTEM in
    Linux)
      if [[ $MACHINE == "x86_64" ]]; then
        ZIG_URL="https://ziglang.org/download/$ZIG_VERSION/zig-linux-x86_64-$ZIG_VERSION.tar.xz"
        CMAKE_URL="https://github.com/Kitware/CMake/releases/download/v$CMAKE_VERSION/cmake-$CMAKE_VERSION-linux-x86_64.tar.gz"
        PLATFORM_DIR="linux-x86_64"
      else
        log "ERROR" "Unsupported Linux architecture: $MACHINE"
        exit 1
      fi
      ;;
    Darwin) # macOS
      if [[ $MACHINE == "x86_64" ]]; then
        ARCH="x86_64"
      else
        ARCH="aarch64"
      fi
      ZIG_URL="https://ziglang.org/download/$ZIG_VERSION/zig-macos-$ARCH-$ZIG_VERSION.tar.xz"
      CMAKE_URL="https://github.com/Kitware/CMake/releases/download/v$CMAKE_VERSION/cmake-$CMAKE_VERSION-macos-universal.tar.gz"
      PLATFORM_DIR="macos-$ARCH"
      ;;
    MINGW*|MSYS*|CYGWIN*|Windows*)
      ZIG_URL="https://ziglang.org/download/$ZIG_VERSION/zig-windows-x86_64-$ZIG_VERSION.zip"
      CMAKE_URL="https://github.com/Kitware/CMake/releases/download/v$CMAKE_VERSION/cmake-$CMAKE_VERSION-windows-x86_64.zip"
      PLATFORM_DIR="windows-x86_64"
      ;;
    *)
      log "ERROR" "Unsupported platform: $SYSTEM"
      exit 1
      ;;
  esac
  
  log "INFO" "Zig URL: $ZIG_URL"
  log "INFO" "CMake URL: $CMAKE_URL"
  
  # Set expected directory names
  if [[ $SYSTEM == "Darwin" ]]; then
    ZIG_DIR="zig-macos-$ARCH-$ZIG_VERSION"
    CMAKE_DIR="cmake-$CMAKE_VERSION-macos-universal"
  else
    ZIG_DIR="zig-$PLATFORM_DIR-$ZIG_VERSION"
    CMAKE_DIR="cmake-$CMAKE_VERSION-$PLATFORM_DIR"
  fi
  
  # Set executable extensions
  if [[ $SYSTEM == MINGW* || $SYSTEM == MSYS* || $SYSTEM == CYGWIN* || $SYSTEM == Windows* ]]; then
    EXE_EXT=".exe"
  else
    EXE_EXT=""
  fi
}

# Download and extract a package
download_and_extract() {
  local url=$1
  local dest_dir=$2
  local filename=$(basename "$url")
  local download_path="$dest_dir/$filename"
  
  mkdir -p "$dest_dir"
  
  if [[ -f "$download_path" ]]; then
    log "INFO" "Archive already exists: $download_path"
  else
    log "INFO" "Downloading $url to $download_path..."
    curl -L -o "$download_path" "$url"
    log "INFO" "Download complete."
  fi
  
  log "INFO" "Extracting $filename..."
  
  if [[ $filename == *.tar.gz ]]; then
    tar -xzf "$download_path" -C "$dest_dir"
  elif [[ $filename == *.tar.xz ]]; then
    tar -xJf "$download_path" -C "$dest_dir"
  elif [[ $filename == *.zip ]]; then
    unzip -q -o "$download_path" -d "$dest_dir"
  else
    log "ERROR" "Unknown archive format: $filename"
    exit 1
  fi
  
  log "INFO" "Extraction complete."
  # Remove the downloaded archive to save space (comment out to keep it)
  # rm "$download_path"
}

# Get Zig
get_zig() {
  ZIG_DOWNLOAD_DIR="$BUILD_DIR/zig_download"
  ZIG_PATH="$ZIG_DOWNLOAD_DIR/$ZIG_DIR"
  ZIG_EXE="$ZIG_PATH/zig$EXE_EXT"
  
  log "INFO" "Looking for Zig at: $ZIG_EXE"
  
  if [[ -f "$ZIG_EXE" ]]; then
    log "INFO" "Found existing Zig installation: $ZIG_PATH"
    # Convert to absolute path now that we know it exists
    ZIG_EXE=$(realpath "$ZIG_EXE")
  else
    log "INFO" "Downloading Zig..."
    download_and_extract "$ZIG_URL" "$ZIG_DOWNLOAD_DIR"
    # Check if the executable exists after download before getting realpath
    if [[ -f "$ZIG_EXE" ]]; then
        ZIG_EXE=$(realpath "$ZIG_EXE")
    else
        log "ERROR" "Zig executable not found at $ZIG_EXE even after download attempt."
        exit 1
    fi
  fi
}

# Get CMake
get_cmake() {
  CMAKE_DOWNLOAD_DIR="$BUILD_DIR/cmake_download"
  CMAKE_PATH="$CMAKE_DOWNLOAD_DIR/$CMAKE_DIR"
  
  # Adjust CMAKE_EXE path based on platform
  if [[ $SYSTEM == "Darwin" ]]; then
      CMAKE_EXE="$CMAKE_PATH/CMake.app/Contents/bin/cmake$EXE_EXT"
  else
      CMAKE_EXE="$CMAKE_PATH/bin/cmake$EXE_EXT"
  fi

  log "INFO" "Looking for CMake at: $CMAKE_EXE"
  
  if [[ -f "$CMAKE_EXE" ]]; then
    log "INFO" "Found existing CMake installation: $CMAKE_PATH"
    # Convert to absolute path now that we know it exists
    CMAKE_EXE=$(realpath "$CMAKE_EXE")
  else
    log "INFO" "Downloading CMake..."
    download_and_extract "$CMAKE_URL" "$CMAKE_DOWNLOAD_DIR"
    # Check if the executable exists after download before getting realpath
    if [[ -f "$CMAKE_EXE" ]]; then
        CMAKE_EXE=$(realpath "$CMAKE_EXE")
    else
        log "ERROR" "CMake executable not found at $CMAKE_EXE even after download attempt."
        exit 1
    fi
  fi
}

# Configure with CMake
configure_cmake() {
  log "INFO" "Configuring project with CMake..."
  mkdir -p "$BUILD_DIR/cmake_build"
  
  # Convert paths to absolute paths
  SOURCE_DIR_ABS=$(realpath "$SOURCE_DIR")
  BUILD_DIR_ABS=$(realpath "$BUILD_DIR/cmake_build")
  INSTALL_DIR_ABS=$(realpath "$INSTALL_DIR")
  
  log "DEBUG" "Using absolute paths:"
  log "DEBUG" "  Source dir: $SOURCE_DIR_ABS"
  log "DEBUG" "  Build dir: $BUILD_DIR_ABS"
  log "DEBUG" "  Install dir: $INSTALL_DIR_ABS"
  log "DEBUG" "  Zig executable: $ZIG_EXE"
  log "DEBUG" "  CMake executable: $CMAKE_EXE"

  # Determine the relative path from BUILD_DIR to the zig executable
  # ZIG_PATH is $BUILD_DIR/zig_download/$ZIG_DIR
  # Wrapper script is in $BUILD_DIR
  ZIG_RELATIVE_PATH="zig_download/$ZIG_DIR/zig$EXE_EXT"

  # make zig_cc and zig_cxx wrapper scripts using the relative path
  echo "#!/bin/bash" > "$BUILD_DIR/zig_cc"
  # Use dirname "$0" to make the path relative to the script's location
  echo "exec \"\$(dirname \"\$0\")/$ZIG_RELATIVE_PATH\" cc \"\$@\"" >> "$BUILD_DIR/zig_cc"

  echo "#!/bin/bash" > "$BUILD_DIR/zig_cxx"
  echo "exec \"\$(dirname \"\$0\")/$ZIG_RELATIVE_PATH\" c++ \"\$@\"" >> "$BUILD_DIR/zig_cxx"

  chmod +x "$BUILD_DIR/zig_cc"
  chmod +x "$BUILD_DIR/zig_cxx"

  # Get absolute paths for the wrapper scripts themselves to pass to CMake
  ZIG_CC=$(realpath "$BUILD_DIR/zig_cc")
  ZIG_CXX=$(realpath "$BUILD_DIR/zig_cxx")

  "$CMAKE_EXE" \
    -S "$SOURCE_DIR_ABS" \
    -B "$BUILD_DIR_ABS" \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR_ABS" \
    -DCMAKE_C_COMPILER="$ZIG_CC" \
    -DCMAKE_CXX_COMPILER="$ZIG_CXX" \
    -DCMAKE_BUILD_TYPE=Release
    
  log "INFO" "CMake configuration complete."
}

# Build with CMake
build_cmake() {
  log "INFO" "Building project..."
  BUILD_DIR_ABS=$(realpath "$BUILD_DIR/cmake_build")
  "$CMAKE_EXE" --build "$BUILD_DIR_ABS" --config Release --parallel
  log "INFO" "Build complete."
}

# Install with CMake
install_cmake() {
  log "INFO" "Installing project..."
  mkdir -p "$INSTALL_DIR"
  BUILD_DIR_ABS=$(realpath "$BUILD_DIR/cmake_build")
  INSTALL_DIR_ABS=$(realpath "$INSTALL_DIR")
  "$CMAKE_EXE" --install "$BUILD_DIR_ABS" --prefix "$INSTALL_DIR_ABS"
  log "INFO" "Installation complete."
}

# Copy executable to target directory (only if --target-dir is specified)
copy_executable() {
  # Check if TARGET_DIR was explicitly provided
  if [[ -z "$TARGET_DIR" ]]; then
    log "INFO" "No explicit --target-dir specified. Skipping final copy step."
    # Ensure INSTALL_DIR exists for the realpath command, create if not (though install_cmake should have)
    mkdir -p "$INSTALL_DIR/bin"
    local final_install_path=$(realpath "$INSTALL_DIR/bin")
    log "INFO" "Build artifacts installed to: $final_install_path"
    log "INFO" "Executable should be at: $final_install_path/my_c_app_exec$EXE_EXT"
    return
  fi

  # Proceed with copy since TARGET_DIR is set
  INSTALL_DIR_ABS=$(realpath "$INSTALL_DIR")
  SRC_EXE_PATH="$INSTALL_DIR_ABS/bin/my_c_app_exec$EXE_EXT"
  DEST_DIR_ABS=$(realpath "$TARGET_DIR")
  DEST_EXE_PATH="$DEST_DIR_ABS/my_c_app_exec$EXE_EXT"

  log "INFO" "Explicit --target-dir specified: $TARGET_DIR"
  
  # Check if source executable exists before attempting copy
  if [[ ! -f "$SRC_EXE_PATH" ]]; then
      log "ERROR" "Source executable not found at '$SRC_EXE_PATH'. Build/install step may have failed or INSTALL_DIR is incorrect."
      # Indicate failure; caller (like pip build script) might need to check exit code
      return 1 
  fi

  log "INFO" "Copying executable from '$SRC_EXE_PATH' to '$DEST_EXE_PATH'"
  mkdir -p "$DEST_DIR_ABS"
  if cp "$SRC_EXE_PATH" "$DEST_EXE_PATH"; then
    chmod +x "$DEST_EXE_PATH"
    log "INFO" "Copy complete."
  else
    log "ERROR" "Failed to copy executable to '$DEST_EXE_PATH'."
    return 1 # Indicate failure
  fi
}

# Clean build artifacts
clean_build() {
  BUILD_DIR_ABS=$(realpath "$BUILD_DIR")
  INSTALL_DIR_ABS=$(realpath "$INSTALL_DIR")
  
  log "INFO" "Cleaning build artifacts..."
  
  # Always clean CMake build directory
  if [[ -d "$BUILD_DIR_ABS/cmake_build" ]]; then
    log "INFO" "Removing CMake build directory: $BUILD_DIR_ABS/cmake_build"
    rm -rf "$BUILD_DIR_ABS/cmake_build"
  fi
  
  # Always clean install directory
  if [[ -d "$INSTALL_DIR_ABS" ]]; then
    log "INFO" "Removing install directory: $INSTALL_DIR_ABS"
    rm -rf "$INSTALL_DIR_ABS"
  fi
  
  log "INFO" "Clean complete."
}

# Create directories
mkdir -p "$BUILD_DIR"
mkdir -p "$INSTALL_DIR"

# Detect platform
detect_platform

# Process steps
if [[ ${#STEPS[@]} -gt 0 ]]; then
  # Process each step in the order specified
  for step in "${STEPS[@]}"; do
    case $step in
      "zig")
        get_zig
        ;;
      "cmake")
        get_cmake
        ;;
      "configure")
        get_zig
        get_cmake
        configure_cmake
        ;;
      "build")
        get_zig
        get_cmake
        configure_cmake
        build_cmake
        ;;
      "install")
        get_zig
        get_cmake
        configure_cmake
        build_cmake
        install_cmake
        ;;
      "copy")
        copy_executable
        ;;
      "clean")
        clean_build
        ;;
      *)
        log "ERROR" "Unknown step: $step"
        exit 1
        ;;
    esac
  done
else
  # Run all steps
  get_zig
  get_cmake
  configure_cmake
  build_cmake
  install_cmake
  copy_executable
fi

log "INFO" "Build process completed successfully." 