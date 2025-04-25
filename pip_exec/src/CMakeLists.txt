cmake_minimum_required(VERSION 3.15) # Minimum version for FetchContent etc.
project(MyCApp C) # Or CXX for C++

# Example using FetchContent for a dependency (e.g., cJSON)
# include(FetchContent)
# FetchContent_Declare(
#   cJSON
#   GIT_REPOSITORY https://github.com/DaveGamble/cJSON.git
#   GIT_TAG        v1.7.15 # Use a specific tag or commit
# )
# FetchContent_MakeAvailable(cJSON)

# Define the executable
add_executable(my_c_app_exec main.c)

# Link dependencies (if any)
# target_link_libraries(my_c_app_exec PRIVATE cjson) # Link cJSON if fetched

# Installation: Define where CMake should place the binary during 'cmake --install'
# The build script will run this and copy the result.
install(TARGETS my_c_app_exec DESTINATION bin) # Install to a 'bin' subdir
