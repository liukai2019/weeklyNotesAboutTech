VS Code user data backup

Created: 2026-03-17 22:39:40

Contents
- settings.json: editor and workbench settings
- keybindings.json: custom keyboard shortcuts
- tasks.json: user-level tasks
- snippets/: user snippets
- extensions.txt: installed extension folder names at backup time

Restore
1. Close VS Code.
2. Copy settings.json, keybindings.json, and tasks.json into %APPDATA%\Code\User\
3. Copy the contents of snippets\ into %APPDATA%\Code\User\snippets\
4. Reinstall extensions as needed, using extensions.txt as the reference list.

Notes
- This backup does not include every extension's internal state.
- If you enable Settings Sync, that is still the safest long-term recovery path.