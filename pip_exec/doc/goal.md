Create a python packge to 
1. Download zig -> provides C compiler and portable libc
2. Download CMake -> compiles using zig cc
3. Use Cmake to configure projects in C or C++, load dependencies using cmake fetch_content
4. Compile c/c++ to executable
5. uvx will run the executable, like `uvx exec_compiled_from_c --args` (uvx is uv tool run from https://github.com/astral-sh/uv)

Be aware, we are not building a manager/launcher for different C/C++ projects. We are providing an example of wrapping a C/C++ executable as a python package, so that our user can download, compile and run the C/C++ code as if it's a python cli by just a pip install call(uv tool run perferred if they have installed uv), removing a lot of burden.

Give me a plan with actionable bullet points to do this, with some code snippets