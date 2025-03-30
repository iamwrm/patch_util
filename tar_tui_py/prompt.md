# User input 1

Use python to write an interactive `tar` tui called `tar_tui.py`, so I can select which file to pack.

you should support selecting files in subdirs 

For keyboard bindings, use space to toggle selection. For output, T for tar, G for tar.gz, P for .patch, Z for tar.zst

Use subprocess to call the cli to do the actual tar, zst, gz operation.

If I toggled a file, the latest status should be reflected. I want to use right key to go to the subdir and left key to go back.
When you go to the subdir, the original dir should also be in the terminal. such as 

Demo:

```
[=] ./subdir1 -> [ ] ./subdir1/file1
                 [X] ./subdir1/file2
                 [X] ./subdir1/file3
                 [ ] ./subdir1/file4
[ ] ./subdir2
[X] ./file5
```

[ ] means not selected, [X] means selected, [=] means subdir is partially selected


We call the python program like
```
python tar_tui.py <optional dir path to start with>

options:
    -f: optional, specify if the file name in the subdir will include it's parent dir path
        e.g. with -f, it's 
            [ ] ./subdir1 -> [ ] ./subdir1/file1
            without -f, it's
            [ ] ./subdir1 -> [ ] ./file1
```
