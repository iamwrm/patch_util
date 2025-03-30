#!/usr/bin/env python3

import curses
import os
import sys
import subprocess
import argparse
from pathlib import Path
import shlex # For safer command display
import tempfile # For patch generation
import shutil # For copying files

# --- Configuration ---
DEFAULT_START_DIR = "."
SELECTION_MARKERS = {
    0: "[ ]",  # Not selected
    1: "[X]",  # Selected
    2: "[=]",  # Partially selected (for directories)
}
DEFAULT_ARCHIVE_BASE_NAME = "archive" # Used for default filenames

# --- Data Structure ---
class TreeNode:
    """Represents a file or directory in the tree."""
    def __init__(self, path, parent=None, include_parent_path=False):
        self.path = Path(path).resolve() # Store absolute path for reliable checks
        self.parent = parent
        self.is_dir = self.path.is_dir()
        self.children = []
        self.children_loaded = False
        self.selected = 0  # 0: None, 1: Selected, 2: Partial
        self.expanded = False
        self.error = None # Store potential permission errors
        self.include_parent_path = include_parent_path # For display name format

    @property
    def name(self):
        """Return the display name based on include_parent_path flag."""
        if self.include_parent_path or self.parent is None:
            # Use path relative to the initial CWD for root nodes or when -f is used
            try:
                # Ensure relative path starts from the initial CWD where script was run
                return f"./{self.path.relative_to(Path.cwd())}"
            except ValueError:
                 # Handle cases where the path is not relative to CWD (e.g., absolute paths given)
                 # Use path relative to the closest parent directory if possible, or absolute
                 try:
                      # Find the root of the displayed tree
                      root_ancestor = self
                      while root_ancestor.parent is not None:
                          root_ancestor = root_ancestor.parent
                      # Display relative to the *starting* directory path if possible
                      return f"./{self.path.relative_to(root_ancestor.path.parent)}" # Relative to parent of root
                 except ValueError:
                      return str(self.path) # Fallback to absolute if unrelated

        else:
             # Use just the basename when -f is not used and it's a child node
             return self.path.name

    def load_children(self):
        """Load immediate children of this directory node."""
        if not self.is_dir or self.children_loaded:
            return
        self.children = []
        self.error = None
        try:
            # Listdir and create nodes, handling potential errors
            items = sorted(list(self.path.iterdir()), key=lambda p: (not p.is_dir(), p.name.lower()))
            for item_path in items:
                try:
                    # Check readability before creating node
                    # is_dir() might raise PermissionError
                    is_item_dir = item_path.is_dir()
                    child_node = TreeNode(item_path, parent=self, include_parent_path=self.include_parent_path)
                    self.children.append(child_node)
                except PermissionError:
                     # Create a node indicating the error
                     error_node = TreeNode(item_path, parent=self, include_parent_path=self.include_parent_path)
                     error_node.error = "Permission Denied"
                     # Try to determine if it was a directory or file, might fail again
                     try: error_node.is_dir = item_path.is_dir()
                     except PermissionError: error_node.is_dir = False # Guess file
                     self.children.append(error_node)
                except OSError as e:
                     error_node = TreeNode(item_path, parent=self, include_parent_path=self.include_parent_path)
                     error_node.error = f"OS Error: {e.strerror}"
                     try: error_node.is_dir = item_path.is_dir()
                     except OSError: error_node.is_dir = False # Guess file
                     self.children.append(error_node)

            self.children_loaded = True
        except PermissionError:
            self.error = "Cannot list directory: Permission Denied"
            self.children_loaded = False # Indicate loading failed
        except OSError as e:
            self.error = f"Cannot list directory: {e.strerror}"
            self.children_loaded = False

    def toggle_selection(self):
        """Toggle selection state (0 -> 1, 1 -> 0)."""
        if self.error: return # Cannot select error nodes

        new_state = 1 if self.selected == 0 else 0
        self._set_selection_recursive(new_state)
        # Update parent states upwards after toggling
        if self.parent:
            self.parent.update_selection_state()

    def _set_selection_recursive(self, state):
        """Recursively set selection state for node and children."""
        self.selected = state
        if self.is_dir:
            # If collapsing selection (state=0), no need to load children
            # If expanding selection (state=1), load children if not already loaded
            if state == 1 and not self.children_loaded:
                self.load_children()
            # Only recurse if children are loaded (or just loaded)
            if self.children_loaded:
                 for child in self.children:
                     if not child.error: # Don't try to select error nodes
                         child._set_selection_recursive(state)

    def update_selection_state(self):
        """Update parent's selection state based on children."""
        if not self.is_dir:
            return

        # Only update if children are loaded, otherwise keep explicit state
        if not self.children_loaded:
            # If node is marked selected (1), but children aren't loaded,
            # it implies a direct selection of the dir. Keep it as 1.
            # If it's 0 or 2, and children aren't loaded, state is indeterminate/explicit. Keep it.
            return

        if not self.children: # Empty directory
             # Keep explicit selection (0 or 1), don't force to 0 or 2
             # If it was explicitly selected (1), keep it 1. If not (0), keep it 0.
             return

        num_selected = 0
        num_partial = 0
        num_children_valid = 0 # Count only non-error children

        for child in self.children:
            if not child.error:
                num_children_valid += 1
                if child.selected == 1:
                    num_selected += 1
                elif child.selected == 2:
                    num_partial += 1

        old_state = self.selected

        if num_children_valid == 0: # All children have errors or dir is empty (handled above)
            # Keep explicitly selected state (1). If not explicitly selected (0 or 2), mark as 0.
            if self.selected != 1: self.selected = 0
             # Do not change state to partial if only error children exist
        elif num_selected == 0 and num_partial == 0:
            self.selected = 0 # All valid children deselected
        elif num_selected == num_children_valid and num_partial == 0:
             # Only fully selected if *all* valid children are fully selected
             self.selected = 1
        else:
            self.selected = 2 # Partial selection among valid children

        # Propagate change upwards if state changed
        if self.parent and self.selected != old_state:
            self.parent.update_selection_state()

    def get_visible_nodes(self):
        """Return a flat list of nodes currently visible in the TUI."""
        nodes = [self]
        if self.is_dir and self.expanded:
            if not self.children_loaded:
                self.load_children() # Load on demand when expanding visually
            for child in self.children:
                # Recursively get nodes from children that are also expanded
                nodes.extend(child.get_visible_nodes())
        return nodes

    def get_selected_paths(self, initial_base_path):
        """Return a list of paths for selected files relative to initial_base_path.
           Directories that are fully selected mean all contents *currently loadable*
           are included recursively. Partial directories mean recurse deeper.
           Returns only *file* paths relative to initial_base_path.
        """
        selected_file_paths = []

        # Base case: Node is a file
        if not self.is_dir:
            if self.selected == 1 and not self.error:
                try:
                    # Ensure path is relative to the initial directory the TUI was started in
                    rel_path = self.path.relative_to(initial_base_path)
                    selected_file_paths.append(str(rel_path))
                except ValueError:
                    # Path is outside the initial base path - skip it for relative archive operations
                    pass # Or log a warning: print(f"Warning: Skipping selected file outside base path: {self.path}")
            return selected_file_paths # Return list containing the file path or empty list

        # Recursive case: Node is a directory
        if self.is_dir and not self.error:
            # If directory is selected (partially or fully), we need to check its children
            if self.selected in [1, 2]:
                # Ensure children are loaded to make decisions
                if not self.children_loaded:
                    self.load_children()

                # If fully selected (1), conceptually all children are selected
                # If partially selected (2), some children/grandchildren are selected
                # In both cases, we recurse into children
                for child in self.children:
                    # If the parent dir is fully selected (1), treat the child as selected (if not an error node)
                    # unless the child itself was later deselected (making parent partial '2').
                    # But the get_selected_paths logic works recursively, so we just call it on children.
                    # If parent is state 1, child will be state 1 (unless error).
                    # If parent is state 2, child state could be 0, 1, or 2.
                    # If parent is state 0, child state must be 0.
                    # The recursive call handles this correctly.
                    selected_file_paths.extend(child.get_selected_paths(initial_base_path))

        return selected_file_paths


# --- TUI Application ---
class TarTUI:
    def __init__(self, stdscr, start_path, include_parent_path):
        self.stdscr = stdscr
        self.start_path = Path(start_path).resolve() # Absolute path of start dir
        self.initial_cwd = Path.cwd() # CWD when script was launched
        self.include_parent_path = include_parent_path

        # Ensure start path exists and is a directory
        if not self.start_path.is_dir():
             raise ValueError(f"Error: Starting path '{start_path}' is not a valid directory.")

        self.root_node = TreeNode(self.start_path, include_parent_path=self.include_parent_path)
        # Expand the root node initially to show its contents
        self.root_node.expanded = True
        self.root_node.load_children() # Load first level

        self.visible_nodes = []
        self.selected_line = 0
        self.top_line = 0 # For scrolling
        self.status = "Navigate: Arrows | Select: Space | Expand/Collapse: Enter/Right/Left | Archive/Patch: T G Z P | Quit: Q"
        self._update_visible_nodes() # Initialize visible nodes


    def _update_visible_nodes(self):
        """Update the flat list of nodes currently visible."""
        # The root node itself might be displayed depending on structure.
        # get_visible_nodes starts from the node it's called on.
        self.visible_nodes = self.root_node.get_visible_nodes()

        # Ensure selected line stays within bounds
        if not self.visible_nodes:
             self.selected_line = 0
        else:
             self.selected_line = max(0, min(self.selected_line, len(self.visible_nodes) - 1))

        self._adjust_scroll()


    def run(self):
        """Main application loop."""
        curses.curs_set(0)  # Hide cursor
        self.stdscr.keypad(True) # Enable special keys (arrows)

        while True:
            self.draw()
            key = self.stdscr.getch()

            action_taken = False # Flag to check if view needs updating

            if key == curses.KEY_UP:
                if self.selected_line > 0:
                    self.selected_line -= 1
                    self._adjust_scroll()
                    action_taken = True # Redraw needed for highlight move
            elif key == curses.KEY_DOWN:
                if self.selected_line < len(self.visible_nodes) - 1:
                    self.selected_line += 1
                    self._adjust_scroll()
                    action_taken = True # Redraw needed for highlight move
            elif key == curses.KEY_RIGHT or key == curses.KEY_ENTER or key == ord('\n'):
                action_taken = self.navigate_into()
            elif key == curses.KEY_LEFT:
                action_taken = self.navigate_out()
            elif key == ord(' '):
                current_node = self.get_current_node()
                if current_node:
                    current_node.toggle_selection()
                    # Update parent state upwards directly after toggle
                    if current_node.parent:
                         current_node.parent.update_selection_state()
                    # Need to update visible nodes because selection markers change
                    self._update_visible_nodes() # Recalculate visible nodes and adjust view
                    action_taken = True # Redraw needed

            elif key in [ord('t'), ord('T')]:
                self.create_archive('tar')
                action_taken = True # Redraw status after potential action
            elif key in [ord('g'), ord('G')]:
                self.create_archive('gz')
                action_taken = True # Redraw status after potential action
            elif key in [ord('z'), ord('Z')]:
                self.create_archive('zst')
                action_taken = True # Redraw status after potential action
            elif key in [ord('p'), ord('P')]:
                self.create_archive('patch')
                action_taken = True # Redraw status after potential action
            elif key in [ord('q'), ord('Q'), 27]: # 27 is ESC
                break

            # No need to update visible nodes unless structure/selection changed
            # if action_taken:
            #    self._update_visible_nodes() # Already called within space handler

            # Ensure selected line is valid after potential view changes (e.g., collapse)
            if self.selected_line >= len(self.visible_nodes) and len(self.visible_nodes) > 0:
                self.selected_line = len(self.visible_nodes) - 1
            elif not self.visible_nodes:
                 self.selected_line = 0


    def get_current_node(self):
        """Get the TreeNode corresponding to the selected line."""
        if 0 <= self.selected_line < len(self.visible_nodes):
            return self.visible_nodes[self.selected_line]
        return None

    def navigate_into(self):
        """Expand directory or move into it. Returns True if view changed."""
        node = self.get_current_node()
        if node and node.is_dir and not node.error:
            if not node.expanded:
                node.expanded = True
                if not node.children_loaded:
                    node.load_children() # Load children on demand
                self._update_visible_nodes() # Update list as children are now visible
                return True # View changed
            # Optional: If already expanded and has children, move selection to first child?
            elif node.children:
               first_child_node = next((child for child in node.children if child in self.visible_nodes), None)
               if first_child_node:
                   try:
                       first_child_index = self.visible_nodes.index(first_child_node)
                       if self.selected_line != first_child_index:
                           self.selected_line = first_child_index
                           self._adjust_scroll()
                           return True # Selection moved, redraw needed
                   except ValueError: pass # Should not happen if first_child_node is from visible_nodes
        return False # No change in expansion state or failed navigation


    def navigate_out(self):
        """Collapse directory or move selection to parent. Returns True if view changed."""
        node = self.get_current_node()
        if node:
            # If the current node is expanded, collapse it first.
            if node.is_dir and node.expanded:
                node.expanded = False
                # Adjust selection to stay on the collapsed node
                try:
                     # We need to recalculate visible nodes first
                     self._update_visible_nodes()
                     # Now find the node in the new list
                     self.selected_line = self.visible_nodes.index(node)
                     self._adjust_scroll()
                except ValueError:
                     # Fallback: if node disappears (e.g. root?), select parent or 0
                     parent = node.parent
                     if parent:
                          try:
                               self.selected_line = self.visible_nodes.index(parent)
                          except ValueError: self.selected_line = 0 # Failsafe
                     else:
                          self.selected_line = 0
                     self._adjust_scroll()
                return True # View structure changed

            # If not expanded (or not a dir), try moving to the parent.
            elif node.parent:
                 try:
                     # Find parent in the current visible list and select it
                     # No need to update visible nodes list just for moving selection
                     parent_index = self.visible_nodes.index(node.parent)
                     if self.selected_line != parent_index: # Only move if not already on parent
                         self.selected_line = parent_index
                         self._adjust_scroll()
                         return True # Selection moved, redraw needed.
                 except ValueError:
                      # Parent might not be visible (e.g. if root is collapsed?)
                       pass
        return False # No change

    def _adjust_scroll(self):
        """Adjust the top_line for scrolling."""
        max_y, max_x = self.stdscr.getmaxyx()
        # Leave space for status bar
        display_height = max_y - 1
        if display_height <= 0: return # Avoid errors if terminal too small

        if self.selected_line < self.top_line:
            self.top_line = self.selected_line
        elif self.selected_line >= self.top_line + display_height:
            self.top_line = self.selected_line - display_height + 1

        # Ensure top_line doesn't go beyond what's possible
        max_top_line = max(0, len(self.visible_nodes) - display_height)
        self.top_line = max(0, min(self.top_line, max_top_line))


    def get_node_display_prefix(self, node):
        """ Get the indentation and selection marker. """
        depth = 0
        temp_node = node
        # Count parents until we reach the initial root_node or None
        while temp_node.parent is not None and temp_node != self.root_node:
             depth += 1
             temp_node = temp_node.parent
        # If the node *is* the root node, depth is -1, adjust to 0 for display
        if node == self.root_node:
            depth = 0 # Root node itself has 0 indentation if displayed

        indent = "  " * depth
        marker = SELECTION_MARKERS.get(node.selected, "[?]")
        # Arrow logic: -> expanded dir, > collapsed dir, ' ' file
        arrow = "->" if node.is_dir and node.expanded else " >" if node.is_dir else "  "
        return f"{indent}{marker}{arrow} "


    def draw(self):
        """Draw the TUI screen."""
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        if max_y <= 1: return # Need at least 2 lines for content + status

        display_height = max_y - 1 # Reserve bottom line for status

        # Draw tree structure
        start_index = self.top_line
        end_index = self.top_line + display_height
        nodes_to_draw = self.visible_nodes[start_index:end_index]

        for i, node in enumerate(nodes_to_draw):
            line_num_in_visible = self.top_line + i # Index in self.visible_nodes
            draw_y = i # Line number on screen (0 to display_height - 1)

            prefix = self.get_node_display_prefix(node)
            display_name = node.name
            suffix = ""
            error_msg = f" ({node.error})" if node.error else ""

            line_text = f"{prefix}{display_name}{suffix}{error_msg}"

            # Ensure we don't try writing past the screen width
            # Truncate intelligently if possible, or just cut
            if len(line_text) >= max_x:
                line_text = line_text[:max_x-1] + "…"

            try:
                attr = curses.A_NORMAL
                if line_num_in_visible == self.selected_line:
                    attr = curses.A_REVERSE # Highlight selected line

                self.stdscr.addstr(draw_y, 0, line_text, attr)
                # Clear the rest of the line if highlighted
                if attr == curses.A_REVERSE:
                    remaining_width = max_x - len(line_text)
                    if remaining_width > 0:
                        self.stdscr.addstr(draw_y, len(line_text), " " * remaining_width, attr)

            except curses.error:
                 # Fallback if addstr fails (e.g., strange character width issues)
                 try:
                      safe_text = line_text[:max_x] # Simple safe clip
                      self.stdscr.addstr(draw_y, 0, safe_text, attr)
                      if attr == curses.A_REVERSE: # Clear rest of line
                           remaining_width = max_x - len(safe_text)
                           if remaining_width > 0:
                               self.stdscr.addstr(draw_y, len(safe_text), " " * remaining_width, attr)
                 except curses.error:
                      pass # Give up drawing this line if it consistently fails


        # Draw status bar
        status_text = self.status[:max_x]
        try:
            self.stdscr.addstr(max_y - 1, 0, status_text, curses.A_REVERSE)
            # Clear rest of status line
            remaining_width = max_x - len(status_text)
            if remaining_width > 0:
                 self.stdscr.addstr(max_y - 1, len(status_text), " " * remaining_width, curses.A_REVERSE)
        except curses.error:
            pass

        self.stdscr.refresh()


    def _get_output_filename(self, default_filename):
        """Temporarily exit curses to get filename input, providing a default."""
        curses.curs_set(1)
        curses.echo()
        curses.nocbreak()
        self.stdscr.keypad(False)

        max_y, max_x = self.stdscr.getmaxyx()
        prompt_line = max_y - 1
        self.stdscr.move(prompt_line, 0)
        self.stdscr.clrtoeol()

        prompt = f"Output filename [Default: {default_filename}]: "
        if len(prompt) >= max_x: prompt = prompt[:max_x-1]

        self.stdscr.addstr(prompt_line, 0, prompt)
        self.stdscr.refresh()

        try:
            # Read input after the prompt
            filename_bytes = self.stdscr.getstr(prompt_line, len(prompt))
            filename = filename_bytes.decode('utf-8').strip()
        except curses.error:
            filename = "" # Assume empty on error

        # Restore curses settings immediately
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)

        if not filename:
            self.status = f"Using default filename: {default_filename}"
            return default_filename
        else:
            self.status = f"Using filename: {filename}"
            return filename


    def create_archive(self, format_type):
        """Collect selected files and call the appropriate command or git logic."""
        # Use the updated get_selected_paths which returns relative file paths
        selected_files_rel = self.root_node.get_selected_paths(self.start_path)

        if not selected_files_rel:
            self.status = "No files selected. Press Q to quit or select files."
            self.draw()
            curses.napms(1500)
            self.status = "Navigate: Arrows | Select: Space | Archive/Patch: T G Z P | Quit: Q"
            return

        output_filename = ""
        cmd = []
        success = False
        temp_dir_obj = None # For patch cleanup

        try:
            # --- Determine command/logic and default filename ---
            if format_type == 'tar':
                extension = 'tar'
                cmd_base = ['tar', '-cf']
            elif format_type == 'gz':
                extension = 'tar.gz'
                cmd_base = ['tar', '-czf']
            elif format_type == 'zst':
                extension = 'tar.zst'
                cmd_base = ['tar', '--zstd', '-cf']
            elif format_type == 'patch':
                extension = 'patch'
                # No cmd_base here, logic is handled separately
            else:
                self.status = f"Internal error: Unknown format '{format_type}'"
                return

            default_filename = f"{DEFAULT_ARCHIVE_BASE_NAME}.{extension}"

            # --- Get output filename from user ---
            output_filename = self._get_output_filename(default_filename)
            if not output_filename:
                self.status = "Operation cancelled (no filename provided)."
                self.draw()
                curses.napms(1500)
                self.status = "Navigate: Arrows | Select: Space | Archive/Patch: T G Z P | Quit: Q"
                return

            # --- Execute the command or patch logic ---
            curses.endwin() # Temporarily leave curses mode
            print("\n" + "=" * 20)
            print(f"Selected {len(selected_files_rel)} file item(s).")

            if format_type == 'patch':
                print("Generating patch using temporary git repository...")
                print(f"Working Directory: {self.initial_cwd}")
                print("-" * 20)

                # Use a context manager for the temporary directory
                temp_dir_obj = tempfile.TemporaryDirectory(prefix="tartui_patch_")
                temp_dir_path = Path(temp_dir_obj.name)

                try:
                    # 1. Copy selected files to temp dir, preserving structure
                    print(f"Copying files to temporary directory: {temp_dir_path}")
                    copy_errors = 0
                    for rel_path_str in selected_files_rel:
                        src_path = self.start_path / rel_path_str
                        dest_path = temp_dir_path / rel_path_str

                        if src_path.is_file(): # Ensure it's a file before copying
                            try:
                                dest_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(src_path, dest_path) # copy2 preserves metadata
                            except Exception as copy_err:
                                print(f"  Error copying {rel_path_str}: {copy_err}", file=sys.stderr)
                                copy_errors += 1
                        # else: skip directories themselves, only copy files listed

                    if copy_errors > 0:
                         print(f"Warning: {copy_errors} errors occurred during file copying.", file=sys.stderr)
                         # Optionally ask user if they want to proceed? For now, continue.

                    # 2. Initialize git repo in temp dir
                    print("Initializing git repository...")
                    git_init_cmd = ['git', 'init']
                    init_proc = subprocess.run(git_init_cmd, cwd=temp_dir_path, capture_output=True, text=True, check=False)
                    if init_proc.returncode != 0:
                         print(f"  Error initializing git: {init_proc.stderr}", file=sys.stderr)
                         raise RuntimeError("git init failed")
                    # Suppress common "hint:" messages from git init if desired
                    # print(init_proc.stdout) # Usually just says initialized empty repo

                    # 3. Add all files
                    print("Adding files to git index...")
                    git_add_cmd = ['git', 'add', '.']
                    add_proc = subprocess.run(git_add_cmd, cwd=temp_dir_path, capture_output=True, text=True, check=False)
                    if add_proc.returncode != 0:
                        print(f"  Error adding files to git: {add_proc.stderr}", file=sys.stderr)
                        # might happen if e.g. file permissions changed or file disappeared
                        raise RuntimeError("git add failed")

                    # 4. Generate diff
                    print("Generating patch (git diff --cached)...")
                    # Use --no-color explicitly if needed, though capture_output usually prevents it
                    git_diff_cmd = ['git', 'diff', '--cached', '--no-color']
                    diff_proc = subprocess.run(git_diff_cmd, cwd=temp_dir_path, capture_output=True, text=True, check=False)

                    # diff --cached returns 0 if no changes staged (shouldn't happen here unless no files selected/copied),
                    # or 0 if successful and there are staged changes. Non-zero indicates an error.
                    if diff_proc.returncode != 0:
                         print(f"  Error generating git diff: {diff_proc.stderr}", file=sys.stderr)
                         raise RuntimeError("git diff failed")

                    # 5. Write patch to file
                    patch_content = diff_proc.stdout
                    output_path_abs = self.initial_cwd / output_filename
                    print(f"Writing patch to {output_path_abs}...")
                    try:
                         with open(output_path_abs, 'w') as f:
                            f.write(patch_content)
                         print(f"\nSuccessfully created patch '{output_filename}'")
                         success = True
                    except IOError as e:
                         print(f"\nError writing patch file '{output_path_abs}': {e}", file=sys.stderr)
                         success = False

                except FileNotFoundError:
                    print("\nError: 'git' command not found. Is git installed and in your PATH?", file=sys.stderr)
                    success = False
                except Exception as patch_err:
                    print(f"\nAn error occurred during patch generation: {patch_err}", file=sys.stderr)
                    success = False
                finally:
                    # TemporaryDirectory context manager handles cleanup on exit/error
                    print(f"Cleaning up temporary directory: {temp_dir_path}")
                    # temp_dir_obj.cleanup() # This is called automatically by context manager

            else: # tar, gz, zst
                cmd = cmd_base + [output_filename] + selected_files_rel
                print(f"Running command:")
                try:
                    print(f"$ {shlex.join(cmd)}")
                except AttributeError: # Fallback for older python
                    print(' '.join(shlex.quote(arg) for arg in cmd))
                print(f"Working Directory: {self.initial_cwd}")
                print("-" * 20)

                # Run the tar command relative to the original start directory
                process = subprocess.run(cmd, check=False, capture_output=True, text=True, cwd=self.start_path) # Run tar from where paths are relative

                if process.stdout:
                    print("Command Output:")
                    print(process.stdout)
                if process.stderr:
                    # Suppress common, non-fatal tar message "Removing leading `../` from member names" or similar
                    # Let's show stderr for tar as it might contain important info
                    print("Command Error Output:", file=sys.stderr)
                    print(process.stderr, file=sys.stderr)

                if process.returncode == 0:
                    print(f"\nSuccessfully created '{output_filename}'")
                    success = True
                else:
                    print(f"\nCommand failed with return code {process.returncode}", file=sys.stderr)
                    success = False

        except FileNotFoundError:
            # Catch tar/zstd not found
            if format_type != 'patch':
                print(f"\nError: Command '{cmd_base[0]}' not found. Is it installed and in your PATH?", file=sys.stderr)
                if format_type == 'zst':
                    print("Note: Creating .tar.zst often requires a modern version of 'tar' with zstd support, or installing 'zstd'.", file=sys.stderr)
            # Git not found handled within the patch block
            success = False
        except Exception as e:
            print(f"\nAn unexpected error occurred during command execution: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            success = False

        print("=" * 20)
        input("Press Enter to return to TUI...")

        # Re-initialize curses screen (necessary after endwin)
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)
        try: # Re-initialize colors if used
             curses.start_color()
             curses.use_default_colors()
        except: pass

        if success:
             self.status = f"Successfully created '{output_filename}'. Press Q to quit."
        else:
             self.status = f"Failed to create archive/patch. Press Q to quit."
        # No automatic exit, draw the final status
        self.draw()


# --- Main Execution ---
def main(stdscr, start_path, include_parent_path):
    try:
        curses.start_color()
        curses.use_default_colors()
    except: pass

    try:
        app = TarTUI(stdscr, start_path, include_parent_path)
        app.run()
    except ValueError as e:
         if curses.isendwin():
             print(e, file=sys.stderr)
         else:
              curses.endwin()
              print(e, file=sys.stderr)
         sys.exit(1)
    except Exception as e:
        if not curses.isendwin():
            curses.endwin()
        print(f"\nAn unexpected error occurred in the TUI: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive TUI for selecting files/dirs to archive or patch.")
    parser.add_argument(
        "start_dir",
        nargs='?',
        default=DEFAULT_START_DIR,
        help=f"Optional directory path to start browsing. Defaults to '{DEFAULT_START_DIR}'."
    )
    parser.add_argument(
        "-f", "--full-path-display",
        action="store_true",
        help="Display full relative path for files inside subdirectories instead of just the filename. Affects display only."
    )

    args = parser.parse_args()

    # Resolve start_dir relative to the *current* working directory
    start_directory = Path(args.start_dir)
    try:
        resolved_start_dir = start_directory.resolve()
    except FileNotFoundError:
         print(f"Error: Starting path '{args.start_dir}' does not exist.", file=sys.stderr)
         sys.exit(1)
    except Exception as e:
         print(f"Error resolving starting path '{args.start_dir}': {e}", file=sys.stderr)
         sys.exit(1)


    if not resolved_start_dir.exists():
        print(f"Error: Starting path '{args.start_dir}' (resolved to '{resolved_start_dir}') does not exist.", file=sys.stderr)
        sys.exit(1)
    if not resolved_start_dir.is_dir():
         print(f"Error: Starting path '{args.start_dir}' (resolved to '{resolved_start_dir}') is not a directory.", file=sys.stderr)
         sys.exit(1)

    # Use curses.wrapper for safety
    try:
        # Pass the *resolved* absolute path to the main function
        curses.wrapper(main, resolved_start_dir, args.full_path_display)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
         # Catch errors that might happen outside the main try/except in main() or during wrapper setup
         if not curses.isendwin():
              try: curses.endwin()
              except: pass # Ignore errors during final endwin attempt
         print(f"\nAn unhandled error occurred: {e}", file=sys.stderr)
         import traceback
         traceback.print_exc()
         sys.exit(1)