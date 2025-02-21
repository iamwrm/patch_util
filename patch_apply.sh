#!/bin/bash
set -e

show_help(){
    echo "Usage: $0 <patch-file> <dst-dir>"
    echo "Apply a patch file to a destination directory"
    echo
    echo "Options:"
    echo "  -h, --help               Show this help message"
    echo
    echo "Examples:"
    echo "  # Apply patch to current directory"
    echo "  $0 ../output.patch ."
}

# Parse command-line arguments
args=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            args+=("$1")
            shift
            ;;
    esac
done

# Validate arguments
if [[ ${#args[@]} -ne 2 ]]; then
    echo "Error: Both patch file and destination directory are required" >&2
    show_help
    exit 1
fi

# Create temporary workspace
temp_dir=$(mktemp -d)

patch_file=$(realpath "${args[0]}")
dst_dir=$(realpath "${args[1]}")

# Apply patch
(
    cd "$temp_dir"
    echo -e "Applying patch \n    from $patch_file \n    to $dst_dir"
    git init --quiet
    git am --quiet "$patch_file"
    rm -rf .git  # Auto-delete repo after applying
    mv ./* "$dst_dir" 2>/dev/null || true  # Handle empty case
    mv ./.??* "$dst_dir" 2>/dev/null || true  # Move hidden files
)

# Cleanup
rm -rf "$temp_dir"
echo -e "Cleaned up temporary workspace \n    $temp_dir"