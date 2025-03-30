# patch_util

This repo works like tar for multiple plain text files. Works great for providing LLM contexts.

## Usage

To run, you can use the following commands:

```bash
# Show help
curl --proto '=https' --tlsv1.2 -sSf \
    https://raw.githubusercontent.com/iamwrm/patch_util/main/patch_make.sh | bash -s  \
    -- -h 

# Make patch
curl --proto '=https' --tlsv1.2 -sSf \
    https://raw.githubusercontent.com/iamwrm/patch_util/main/patch_make.sh | bash -s  \
    -- -i "*.sh" .

curl --proto '=https' --tlsv1.2 -sSf \
    https://raw.githubusercontent.com/iamwrm/patch_util/main/patch_make.sh | bash -s  \
    -- -i "*.cpp" -i "*.h" -i "*.hpp" -i "CMakeLists.txt" -i "*.sh" -i "*.fbs" -e "build/" try_flatbuffers

# ==============================

# Apply patch
mkdir new_dir
curl --proto '=https' --tlsv1.2 -sSf \
    https://raw.githubusercontent.com/iamwrm/patch_util/main/patch_apply.sh | bash -s  \
    -- ./output.patch new_dir
```

Check `output.patch` to see the patch file.


## V2 with tar_tui.py

```bash
uvx --from git+https://github.com/iamwrm/patch_util#subdirectory=tar_tui_py tar_tui
```

## install lazygit

```bash
mkdir -p ~/.local/bin
curl -sL https://github.com/jesseduffield/lazygit/releases/download/v0.48.0/lazygit_0.48.0_Linux_x86_64.tar.gz | tar xz -C ~/.local/bin lazygit
```
