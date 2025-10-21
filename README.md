# patch_util

This repo works like tar for multiple plain text files. Works great for providing LLM contexts.

## Usage - V2 (Recommended)

Interactive TUI for selecting files and creating archives or patches:

```bash
# Run with uvx (no installation required)
uvx --from git+https://github.com/iamwrm/patch_util#subdirectory=tar_tui_py tar_tui

# Or specify a starting directory
uvx --from git+https://github.com/iamwrm/patch_util#subdirectory=tar_tui_py tar_tui /path/to/dir

# Display full relative paths
uvx --from git+https://github.com/iamwrm/patch_util#subdirectory=tar_tui_py tar_tui -f
```

### Features

- 📁 Interactive file browser with tree view
- ✅ Multi-select files and directories
- 📦 Create tar, tar.gz, or tar.zst archives
- 🔧 Generate patches using git diff
- ⌨️ Keyboard navigation (arrows, space, enter)

### Keyboard Controls

- **Arrows**: Navigate
- **Space**: Toggle selection
- **Enter/Right**: Expand directory
- **Left**: Collapse directory
- **T**: Create .tar archive
- **G**: Create .tar.gz archive
- **Z**: Create .tar.zst archive
- **P**: Create .patch file
- **Q**: Quit

### Requirements

- Python 3
- git (required for patch generation)
