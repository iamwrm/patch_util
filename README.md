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

# Apply patch
mkdir new_dir
curl --proto '=https' --tlsv1.2 -sSf \
    https://raw.githubusercontent.com/iamwrm/patch_util/main/patch_apply.sh | bash -s  \
    -- ./output.patch new_dir
```

Check `output.patch` to see the patch file.


