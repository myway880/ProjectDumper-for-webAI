# dump_project.py
# --- Imports Section ---
from core_dump import *
from tkinter import filedialog, messagebox, ttk, simpledialog
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
# TODO: Remove this line at the end of development to restore bytecode caching.
# --- Main Function Section ---
def main():
    global default_start_dir, default_output_dir, default_output_base, default_minify, default_max_part_size, default_format, default_split_large_files, default_single_file_limit, default_include_hashes
    parser = argparse.ArgumentParser(description="Project Dump Tool")
    parser.add_argument("input", nargs="?", default=None, help="Input directory or file path")
    parser.add_argument("--output", "-o", help="Output path (directory or file)")
    parser.add_argument("--output-base", default=None, help="Output file base name")
    parser.add_argument("--extensions", help="Semicolon-separated extensions")
    parser.add_argument("--include", help="Semicolon-separated include patterns")
    parser.add_argument("--exclude", help="Semicolon-separated exclude patterns")
    parser.add_argument("--max-part-size", type=int, default=default_max_part_size)
    parser.add_argument("--format", choices=["md", "txt"], default=default_format)
    parser.add_argument("--single-file-limit", type=int, default=default_single_file_limit)
    parser.add_argument("--minify", action="store_true", default=default_minify)
    parser.add_argument("--hashes", action="store_true", default=default_include_hashes)
    parser.add_argument("--no-split", dest="no_split", action="store_true")
    parser.add_argument("--gui", action="store_true", help="Force GUI mode")
    parser.add_argument("--no-gui", action="store_true", help="Force CLI mode")
    parser.add_argument("--backup", action="store_true", help="Create archive backup instead of dump")
    parser.add_argument("--profile", choices=list(default_profiles.keys()))
    parser.add_argument("--max-output-parts", type=int, default=0, help="Max number of output files (0 for no limit)")
    parser.add_argument("--preset", help="Preset name for specific file set")
    parser.add_argument("--use-placeholders", action="store_true", default=default_use_placeholders)
    parser.add_argument("--include-tree", action="store_true", default=default_include_tree)
    parser.add_argument("--no-include-tree", action="store_false", dest="include_tree")
    parser.add_argument("--parse-git", action="store_true", default=default_parse_git)
    parser.add_argument("--no-parse-git", action="store_false", dest="parse_git")
    parser.add_argument("--timestamp", action="store_true", default=default_timestamp)
    parser.add_argument("--include-binary", action="store_true", default=False)
    parser.add_argument("--full-backup", action="store_true", default=False)
    parser.add_argument("--input-type", choices=["Local", "GitHub"], default="Local")
    args = parser.parse_args()
    # Update config with args for GUI prefill (non-path settings only)
    custom_config["LastMinify"] = args.minify
    custom_config["LastIncludeHashes"] = args.hashes
    custom_config["LastMaxPartSize"] = args.max_part_size
    custom_config["LastFormat"] = args.format
    custom_config["LastSplitLargeFiles"] = not args.no_split
    custom_config["LastSingleFileLimit"] = args.single_file_limit
    if args.profile:
        custom_config["LastProfile"] = args.profile
        prof = custom_config["Profiles"][args.profile]
        custom_config["Extensions"] = prof["Extensions"]
        custom_config["IncludePatterns"] = prof["IncludePatterns"]
        custom_config["Exclude"] = prof["Exclude"]
    if args.extensions:
        custom_config["Extensions"] = parse_extensions(args.extensions)
    if args.include:
        custom_config["IncludePatterns"] = parse_list(args.include)
    if args.exclude:
        custom_config["Exclude"] = parse_list(args.exclude)
    # Reload defaults after update
    default_start_dir = custom_config.get("LastStartDir", os.getcwd())
    default_output_dir = custom_config.get("LastOutputDir", default_start_dir)
    default_output_base = custom_config.get("LastOutputBase", "project-dump")
    default_minify = custom_config.get("LastMinify", False)
    default_max_part_size = int(custom_config.get("LastMaxPartSize", 19000))
    default_format = custom_config.get("LastFormat", "txt") if custom_config.get("LastFormat") in ["md", "txt"] else "txt"
    default_split_large_files = custom_config.get("LastSplitLargeFiles", True)
    default_single_file_limit = int(custom_config.get("LastSingleFileLimit", 15000))
    default_include_hashes = custom_config.get("LastIncludeHashes", False)
    # Override defaults with CLI args for paths (in memory only, do not save to config)
    # Comment: LastStartDir and LastOutputDir are not saved to config to prevent overriding CLI arguments in future runs.
    has_args = len(sys.argv) > 1
    if has_args:
        start_dir = args.input if args.input is not None else os.getcwd()
        output_dir = None
        output_base_from_args = args.output_base
        if args.output:
            if os.path.isdir(args.output):
                output_dir = args.output
            else:
                output_dir = os.path.dirname(os.path.abspath(args.output))
                output_base_from_args = os.path.splitext(os.path.basename(args.output))[0]
        if output_dir is None:
            if os.path.isfile(start_dir):
                output_dir = os.path.dirname(start_dir)
            else:
                output_dir = start_dir
        default_start_dir = start_dir
        default_output_dir = output_dir
        default_output_base = output_base_from_args or default_output_base
    if args.no_gui or (has_args and not args.gui):
        return cli_run(args)
    else:
        # Fallback to CLI if tkinter import fails (e.g., headless env)
        try:
            import tkinter as tk
            from tk_ui import DumpApp
            root = tk.Tk()
            app = DumpApp(root)
            root.mainloop()
            return 0
        except ImportError as e:
            print(f"GUI not available ({e}). Falling back to CLI.")
            return cli_run(args)
        except Exception as e:
            print(f"GUI error: {e}. Falling back to CLI.")
            return cli_run(args)
    # TODO (Enhancement): Add --version flag and --help with examples for CLI.
    # TODO (Feature): Support batch mode for multiple inputs via --input-list file.
    # TODO (Design Improvement): Use click or typer for more polished CLI with colors and progress bars.
if __name__ == "__main__":
    sys.exit(main())