#!/bin/bash
set -e

show_help() {
    echo "Usage: $0 [OPTIONS] <source-dir>"
    echo "Generate a Git patch using rsync-style include/exclude patterns"
    echo
    echo "Options:"
    echo "  -e, --exclude PATTERN    Exclude files matching PATTERN (rsync syntax)"
    echo "  -i, --include PATTERN    Include files matching PATTERN (rsync syntax)"
    echo "  -o, --output FILE        Specify output patch file (default: output.patch)"
    echo "  -h, --help               Show this help message"
    echo
    echo "Examples:"
    echo "  # Include all .rs files but exclude tests"
    echo "  $0 -i '**.rs' -e '*_test.rs' ."
    echo
    echo "  # Include entire directory except logs and tmpdir"
    echo "  $0 -i '**' -e 'logs/' -e 'tmpdir/' /path/to/src"
    echo
    echo "  # Include config files but exclude secrets"
    echo "  $0 -i 'config/**' -e '*.secret' ."
}

# Parse command-line arguments
args=()
output_file="output.patch"
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--exclude)
            excludes+=("--exclude=$2")
            shift 2
            ;;
        -i|--include)
            includes+=("--include=$2")
            shift 2
            ;;
        -o|--output)
            output_file="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            echo "Error: Unknown option $1" >&2
            exit 1
            ;;
        *)
            args+=("$1")
            shift
            ;;
    esac
done

# Validate arguments
if [[ ${#args[@]} -ne 1 ]]; then
    show_help >&2
    exit 1
fi

source_dir=$(realpath "${args[0]}")
temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT

# Configure neutral commit identity
export GIT_AUTHOR_NAME="Patch Creator"
export GIT_AUTHOR_EMAIL="patch@example.com"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

# Build rsync command with patterns
rsync_cmd=(
    rsync -aR
    --prune-empty-dirs
    "${excludes[@]}"
    "${includes[@]}"
    --exclude="*"  # Required to override default include-all
    . "$temp_dir"
)

(
    cd "$source_dir"
    # Print and execute rsync command
    echo "Executing: ${rsync_cmd[@]}" >&2
    "${rsync_cmd[@]}"
)

# Generate patch
(
    cd "$temp_dir"
    if [[ -n $(find . -mindepth 1 -print -quit) ]]; then
        git init --quiet
        git add . >/dev/null
        git commit --quiet -m "Patch commit"
        git format-patch --root --stdout > "../$output_file"
    else
        echo "Error: No files matched patterns" >&2
        exit 1
    fi
)

mv "$temp_dir/../$output_file" .
echo "Patch created: $output_file"