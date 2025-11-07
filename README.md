# Project Dump Tool

## Description

The Project Dump Tool is a versatile utility designed to generate a comprehensive dump of project files, optimized for sharing with AI models like Grok in a web browser interface. It processes local directories or GitHub repositories, filters files based on extensions and patterns, and outputs formatted text files (MD or TXT) suitable for pasting into AI context windows. The tool supports minification, hashing, splitting large files, and backups, making it ideal for developers who need to quickly provide code context to AI assistants without manual copying.

Main use case: Create a code dump of your project to share with an AI (e.g., Grok) via a web browser, ensuring the content fits within context limits while preserving essential structure and details.

## Features

- **File Filtering**: Include/exclude files based on extensions, patterns, .gitignore, and project-specific configs.
- **Output Formatting**: Generate MD or TXT files with optional timestamps, project tree, and file hashes.
- **Minification**: Minify JS/TS/CSS/HTML files to reduce size.
- **Large File Handling**: Split large files or use placeholders to fit AI context windows.
- **Backup System**: Create compressed backups (ZIP or 7Z) of filtered or full projects.
- **Preset Support**: Define and use presets for specific file sets.
- **GitHub Integration**: Dump directly from GitHub URLs.
- **GUI and CLI**: User-friendly Tkinter GUI with mini/tray modes; full CLI support.
- **Profiles**: Predefined and custom profiles for different development languages (e.g., Web Dev, Python, C++).
- **Automation**: Generate BAT files for quick dumping and backups on Windows.
- **Scheduling**: Auto-save settings and timed backups in GUI mode.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/project-dump-tool.git
   cd project-dump-tool
   ```

2. Install dependencies (Python 3.8+ required):
   ```
   pip install -r requirements.txt
   ```
   - Note: For 7Z backups, install `py7zr` manually if needed: `pip install py7zr`.
   - For minification, install optional tools like `terser` (Node.js), `cleancss`, or `html-minifier` via npm.

3. Run the tool:
   - GUI: `python dump_project.py`
   - CLI: `python dump_project.py --help` for options.

## Usage

### GUI Mode
- Launch the app and configure settings (profiles, patterns, output).
- Select project directory or GitHub URL.
- Click "Run Dump" to generate output files.
- Use "Backup" for archives, "Restore" to extract backups.

### CLI Mode
- Basic dump: `python dump_project.py /path/to/project --output /output/dir`
- With options: `python dump_project.py /path/to/project --minify --hashes --format md --preset mypreset`
- Backup: `python dump_project.py /path/to/project --backup --full-backup`

For detailed CLI options, run `python dump_project.py --help`.

## Windows Context Menu Integration

To add "Dump Project" to the right-click menu for folders on Windows 10, create and run a `.reg` file with the following content. Replace `C:\\Path\\To\\dump_project.py` with the actual path to your script (use double backslashes).

```
Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\Directory\shell\DumpProject]
@="Dump Project"

[HKEY_CLASSES_ROOT\Directory\shell\DumpProject\command]
@="python \"C:\\Path\\To\\dump_project.py\" \"%1\""
```

Save as `add_dump_context.reg` and double-click to import. To remove, create and run:

```
Windows Registry Editor Version 5.00

[-HKEY_CLASSES_ROOT\Directory\shell\DumpProject]
```

**Warning**: Editing the registry can cause issues; use at your own risk.

## License

MIT License

Copyright (c) 2025 [myway880]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Additional Information

- **Configuration**: Settings are saved in `dump-config.json`. Project-specific configs in `.dump-project.json`.
- **Logs**: Check `dump-project.log` for details.
- **Dependencies**: Tkinter (GUI), py7zr (optional for 7Z), minifiers (optional).
- **Contributions**: Pull requests welcome for new profiles or features.
- **Issues**: Report bugs on GitHub issues page.

For questions, open an issue or contact the maintainer.
