#!/usr/bin/env python3

import curses
import os
import sys
import subprocess
import argparse
import tempfile
import shutil
from pathlib import Path

# Configuration
DEFAULT_START_DIR = "."
DEFAULT_ARCHIVE_NAME = "archive"

class FileNode:
    """Simplified file/directory node with basic selection state."""
    
    def __init__(self, path, parent=None):
        self.path = Path(path).resolve()
        self.parent = parent
        self.is_dir = self.path.is_dir()
        self.children = []
        self.children_loaded = False
        self.selected = False
        self.expanded = False
        self.error = None
        
    @property
    def name(self):
        """Display name for the node."""
        if self.parent is None:
            return f"./{self.path.name}"
        return self.path.name
    
    def load_children(self):
        """Load directory children on demand."""
        if not self.is_dir or self.children_loaded:
            return
            
        self.children = []
        try:
            items = sorted(self.path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for item in items:
                try:
                    child = FileNode(item, self)
                    self.children.append(child)
                except (PermissionError, OSError) as e:
                    child = FileNode(item, self)
                    child.error = str(e)
                    self.children.append(child)
            self.children_loaded = True
        except (PermissionError, OSError) as e:
            self.error = str(e)
    
    def toggle_selection(self):
        """Toggle selection state and propagate to children."""
        if self.error:
            return
            
        self.selected = not self.selected
        if self.is_dir and self.children_loaded:
            self._set_children_selection(self.selected)
    
    def _set_children_selection(self, selected):
        """Recursively set selection state for all children."""
        for child in self.children:
            if not child.error:
                child.selected = selected
                if child.is_dir and child.children_loaded:
                    child._set_children_selection(selected)
    
    def get_visible_nodes(self):
        """Return flat list of visible nodes for display."""
        nodes = [self]
        if self.is_dir and self.expanded:
            if not self.children_loaded:
                self.load_children()
            for child in self.children:
                nodes.extend(child.get_visible_nodes())
        return nodes
    
    def get_selected_files(self, base_path):
        """Return list of selected file paths relative to base_path."""
        files = []
        
        if not self.is_dir and self.selected and not self.error:
            try:
                rel_path = self.path.relative_to(base_path)
                files.append(str(rel_path))
            except ValueError:
                pass
        elif self.is_dir and not self.error:
            if not self.children_loaded:
                self.load_children()
            for child in self.children:
                files.extend(child.get_selected_files(base_path))
                
        return files

class TarTUI:
    """Simplified TUI for creating archives from selected files."""
    
    def __init__(self, stdscr, start_path):
        self.stdscr = stdscr
        self.start_path = Path(start_path).resolve()
        self.root = FileNode(self.start_path)
        self.root.expanded = True
        self.root.load_children()
        
        self.visible_nodes = []
        self.selected_line = 0
        self.top_line = 0
        self.status = "Space: select | Enter: expand | T/G/Z: archive | P: patch | Q: quit"
        
        self._update_display()
    
    def _update_display(self):
        """Update visible nodes and adjust selection bounds."""
        self.visible_nodes = self.root.get_visible_nodes()
        if self.visible_nodes:
            self.selected_line = max(0, min(self.selected_line, len(self.visible_nodes) - 1))
        else:
            self.selected_line = 0
        self._adjust_scroll()
    
    def _adjust_scroll(self):
        """Adjust scroll position to keep selected line visible."""
        max_y, _ = self.stdscr.getmaxyx()
        display_height = max_y - 1  # Reserve line for status
        
        if self.selected_line < self.top_line:
            self.top_line = self.selected_line
        elif self.selected_line >= self.top_line + display_height:
            self.top_line = self.selected_line - display_height + 1
        
        max_top = max(0, len(self.visible_nodes) - display_height)
        self.top_line = max(0, min(self.top_line, max_top))
    
    def _get_current_node(self):
        """Get currently selected node."""
        if 0 <= self.selected_line < len(self.visible_nodes):
            return self.visible_nodes[self.selected_line]
        return None
    
    def _get_node_depth(self, node):
        """Calculate display depth for indentation."""
        depth = 0
        current = node
        while current.parent and current != self.root:
            depth += 1
            current = current.parent
        return depth
    
    def run(self):
        """Main event loop."""
        curses.curs_set(0)
        self.stdscr.keypad(True)
        
        while True:
            self._draw()
            key = self.stdscr.getch()
            
            if key == curses.KEY_UP and self.selected_line > 0:
                self.selected_line -= 1
                self._adjust_scroll()
            elif key == curses.KEY_DOWN and self.selected_line < len(self.visible_nodes) - 1:
                self.selected_line += 1
                self._adjust_scroll()
            elif key in (curses.KEY_RIGHT, curses.KEY_ENTER, ord('\n')):
                self._expand_node()
            elif key == curses.KEY_LEFT:
                self._collapse_node()
            elif key == ord(' '):
                self._toggle_selection()
            elif key in (ord('t'), ord('T')):
                self._create_archive('tar')
            elif key in (ord('g'), ord('G')):
                self._create_archive('tar.gz')
            elif key in (ord('z'), ord('Z')):
                self._create_archive('tar.zst')
            elif key in (ord('p'), ord('P')):
                self._create_patch()
            elif key in (ord('q'), ord('Q'), 27):  # Q or ESC
                break
    
    def _expand_node(self):
        """Expand current directory node."""
        node = self._get_current_node()
        if node and node.is_dir and not node.error and not node.expanded:
            node.expanded = True
            node.load_children()
            self._update_display()
    
    def _collapse_node(self):
        """Collapse current directory node."""
        node = self._get_current_node()
        if node and node.is_dir and node.expanded:
            node.expanded = False
            self._update_display()
        elif node and node.parent:
            # Move to parent
            try:
                parent_idx = self.visible_nodes.index(node.parent)
                self.selected_line = parent_idx
                self._adjust_scroll()
            except ValueError:
                pass
    
    def _toggle_selection(self):
        """Toggle selection of current node."""
        node = self._get_current_node()
        if node:
            node.toggle_selection()
            self._update_display()
    
    def _draw(self):
        """Draw the TUI interface."""
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        
        # Draw file tree
        display_height = max_y - 1
        end_idx = min(self.top_line + display_height, len(self.visible_nodes))
        
        for i in range(self.top_line, end_idx):
            y = i - self.top_line
            node = self.visible_nodes[i]
            
            # Build display line
            depth = self._get_node_depth(node)
            indent = "  " * depth
            marker = "[X]" if node.selected else "[ ]"
            
            if node.is_dir:
                arrow = "-> " if node.expanded else " > "
            else:
                arrow = "   "
            
            name = node.name
            error_suffix = f" ({node.error})" if node.error else ""
            line = f"{indent}{marker}{arrow}{name}{error_suffix}"
            
            # Truncate if too long
            if len(line) >= max_x:
                line = line[:max_x-1]
            
            # Draw with highlighting if selected
            attr = curses.A_REVERSE if i == self.selected_line else curses.A_NORMAL
            try:
                self.stdscr.addstr(y, 0, line, attr)
                if attr == curses.A_REVERSE:
                    # Fill rest of line with highlight
                    remaining = max_x - len(line)
                    if remaining > 0:
                        self.stdscr.addstr(y, len(line), " " * remaining, attr)
            except curses.error:
                pass
        
        # Draw status bar
        try:
            status = self.status[:max_x]
            self.stdscr.addstr(max_y - 1, 0, status, curses.A_REVERSE)
            remaining = max_x - len(status)
            if remaining > 0:
                self.stdscr.addstr(max_y - 1, len(status), " " * remaining, curses.A_REVERSE)
        except curses.error:
            pass
        
        self.stdscr.refresh()
    
    def _get_filename(self, default_name):
        """Get output filename from user."""
        curses.echo()
        curses.curs_set(1)
        
        max_y, max_x = self.stdscr.getmaxyx()
        prompt = f"Filename [{default_name}]: "
        
        self.stdscr.move(max_y - 1, 0)
        self.stdscr.clrtoeol()
        self.stdscr.addstr(max_y - 1, 0, prompt)
        self.stdscr.refresh()
        
        try:
            filename = self.stdscr.getstr(max_y - 1, len(prompt)).decode('utf-8').strip()
        except curses.error:
            filename = ""
        
        curses.noecho()
        curses.curs_set(0)
        
        return filename if filename else default_name
    
    def _create_archive(self, format_type):
        """Create archive of selected files."""
        selected_files = self.root.get_selected_files(self.start_path)
        
        if not selected_files:
            self.status = "No files selected!"
            return
        
        # Get filename
        default_name = f"{DEFAULT_ARCHIVE_NAME}.{format_type}"
        filename = self._get_filename(default_name)
        
        # Build command
        if format_type == 'tar':
            cmd = ['tar', '-cf', filename] + selected_files
        elif format_type == 'tar.gz':
            cmd = ['tar', '-czf', filename] + selected_files
        elif format_type == 'tar.zst':
            cmd = ['tar', '--zstd', '-cf', filename] + selected_files
        
        self._run_command(cmd, f"Created {filename}")
    
    def _create_patch(self):
        """Create git patch of selected files."""
        selected_files = self.root.get_selected_files(self.start_path)
        
        if not selected_files:
            self.status = "No files selected!"
            return
        
        filename = self._get_filename(f"{DEFAULT_ARCHIVE_NAME}.patch")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Copy files to temp directory
                for file_rel in selected_files:
                    src = self.start_path / file_rel
                    dst = temp_path / file_rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                
                # Initialize git and create patch
                subprocess.run(['git', 'init'], cwd=temp_path, check=True, capture_output=True)
                subprocess.run(['git', 'add', '.'], cwd=temp_path, check=True, capture_output=True)
                result = subprocess.run(['git', 'diff', '--cached'], cwd=temp_path, 
                                      capture_output=True, text=True, check=True)
                
                # Write patch file
                with open(filename, 'w') as f:
                    f.write(result.stdout)
                
                self.status = f"Created {filename}"
        
        except subprocess.CalledProcessError as e:
            self.status = f"Error creating patch: {e}"
        except Exception as e:
            self.status = f"Error: {e}"
    
    def _run_command(self, cmd, success_msg):
        """Run external command and show result."""
        curses.endwin()
        
        print(f"\nRunning: {' '.join(cmd)}")
        print(f"Working directory: {self.start_path}")
        print("-" * 40)
        
        try:
            result = subprocess.run(cmd, cwd=self.start_path, check=True, 
                                  capture_output=True, text=True)
            print(success_msg)
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {e}")
            if e.stderr:
                print(f"Error: {e.stderr}")
        except FileNotFoundError:
            print(f"Command not found: {cmd[0]}")
        
        input("\nPress Enter to continue...")
        
        # Reinitialize curses
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="TUI for creating archives from selected files")
    parser.add_argument("start_dir", nargs='?', default=DEFAULT_START_DIR,
                       help="Directory to start browsing from")
    args = parser.parse_args()
    
    start_path = Path(args.start_dir).resolve()
    if not start_path.is_dir():
        print(f"Error: {start_path} is not a valid directory", file=sys.stderr)
        sys.exit(1)
    
    try:
        curses.wrapper(lambda stdscr: TarTUI(stdscr, start_path).run())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()