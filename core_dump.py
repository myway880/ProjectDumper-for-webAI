# core_dump.py
# --- Imports Section ---
import json
import os
import re
import hashlib
import tempfile
import subprocess
from collections import defaultdict
import zipfile
from pathlib import Path
from datetime import datetime
import sys
import argparse
import shutil
import base64
from profiles import default_profiles # Imported from separate file for better modularity
import logging
try:
    import py7zr # type: ignore
except ImportError:
    py7zr = None
# --- Constants and Logging Setup Section ---
log_path = Path(__file__).parent / "dump-project.log"
logging.basicConfig(filename=str(log_path), level=logging.INFO, format='%(asctime)s - %(message)s', filemode='w')
logging.info(f"Starting script at {datetime.now()}")
# --- Config Loading Section ---
config_path = Path(__file__).parent / "dump-config.json"
logging.info(f"Config path: {config_path}")
custom_config = {}
if config_path.exists():
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
        logging.info("Loaded custom config from dump-config.json")
        custom_config = loaded_config
        if custom_config.get("LastOutputBase") == "project-dump":
            custom_config.pop("LastOutputBase", None)
            logging.info("Ignored default 'LastOutputBase' from config")
        # Migrate if needed
        if "LastIncludeHash" in custom_config:
            custom_config["LastIncludeHashes"] = custom_config["LastIncludeHash"]
            del custom_config["LastIncludeHash"]
            logging.info("Migrated old 'LastIncludeHash' to 'LastIncludeHashes'")
        if "Profiles" not in custom_config or not isinstance(custom_config["Profiles"], dict):
            custom_config["Profiles"] = default_profiles
    except Exception as e:
        logging.error(f"Failed to load dump-config.json: {e}")
else:
    logging.info("No dump-config.json found, using default config")
# --- Default Configurations Section ---
# Note: These paths are loaded from config only if no CLI args; CLI args override in memory for the session. Do not save LastStartDir or LastOutputDir to config when CLI args provided, to avoid overriding CLI.
default_start_dir = custom_config.get("LastStartDir", os.getcwd())
default_output_dir = custom_config.get("LastOutputDir", default_start_dir)
default_output_base = custom_config.get("LastOutputBase", "project-dump")
default_minify = custom_config.get("LastMinify", False)
default_max_part_size = int(custom_config.get("LastMaxPartSize", 19000))
default_format = custom_config.get("LastFormat", "txt") if custom_config.get("LastFormat") in ["md", "txt"] else "txt"
default_split_large_files = custom_config.get("LastSplitLargeFiles", True)
default_single_file_limit = int(custom_config.get("LastSingleFileLimit", 15000))
default_include_hashes = custom_config.get("LastIncludeHashes", False)
default_form_width = int(custom_config.get("LastFormWidth", 924))
default_form_height = int(custom_config.get("LastFormHeight", 740))
default_form_x = int(custom_config.get("LastFormX", 100))
default_form_y = int(custom_config.get("LastFormY", 100))
default_dynamic_patterns = custom_config.get("DynamicPatterns", [])
default_is_exclude_dynamic = custom_config.get("IsExcludeDynamic", False)
default_input_type = custom_config.get("LastInputType", "Local")
default_use_placeholders = custom_config.get("LastUsePlaceholders", False)
default_include_tree = custom_config.get("LastIncludeTree", True)
default_parse_git = custom_config.get("LastParseGit", True)
default_timestamp = custom_config.get("LastTimestamp", False)
default_profile = custom_config.get("LastProfile", "Web Dev") # Default to Web Dev on first start
default_max_output_parts = int(custom_config.get("LastMaxOutputParts", 0)) # 0 means no limit
default_use_default_backup_path = custom_config.get("UseDefaultBackupPath", True)
# --- Language Mapping Section ---
ext_to_lang = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".svelte": "svelte",
    ".vue": "vue",
    ".json": "json",
    ".xml": "xml",
    ".cs": "csharp",
    ".xaml": "xml",
    ".csproj": "xml",
    ".sln": "ini",
    ".bat": "batch",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    # Add more mappings as needed for supported extensions
}
# --- Helper Functions Section ---
def log_write(message):
    logging.info(message)
def log_message(message):
    print(message)
    log_write(message)
def parse_list(s):
    if not s:
        return []
    return [p.strip() for p in s.split(';') if p.strip()]
def parse_extensions(s):
    if not s:
        return []
    exts = parse_list(s)
    return [f".{e}" if not e.startswith('.') else e for e in exts]
def glob_to_regex(pattern):
    try:
        temp_any = "TEMP_RECURSIVE_ANY"
        regex = re.sub(r'\\', '/', pattern)
        regex = re.sub(r'([.+^${}()|[\]])', r'\\\1', regex)
        regex = regex.replace('**', temp_any)
        regex = re.sub(r'\*', '[^/]*', regex)
        regex = regex.replace(temp_any, '.*')
        return f"^{regex}$"
    except re.error as e:
        raise ValueError(f"Invalid glob pattern '{pattern}': {e}")
def parse_gitignore(gitignore_path):
    patterns = []
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and stripped != '!':
                    if stripped.startswith('/'):
                        patterns.append(stripped[1:])
                    elif stripped.endswith('/'):
                        patterns.append(stripped[:-1] + '/**')
                    else:
                        patterns.append('**/' + stripped)
    except Exception as e:
        log_message(f"Error parsing .gitignore: {e}")
    return patterns
def build_tree_from_files(all_files, root_dir):
    tree = defaultdict(dict)
    for file_path in all_files:
        rel_path = Path(file_path).relative_to(root_dir)
        parts = rel_path.parts
        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = None
    def render_tree(node, prefix="", is_last=True):
        lines = []
        items = sorted(node.keys())
        for i, key in enumerate(items):
            child = node[key]
            is_last_item = i == len(items) - 1
            line_prefix = prefix + ("└── " if is_last_item else "├── ")
            if isinstance(child, dict) and child:
                lines.append(f"{line_prefix}{key}/")
                new_prefix = prefix + (" " if is_last_item else "│ ")
                lines.extend(render_tree(child, new_prefix, is_last_item))
            else:
                lines.append(f"{line_prefix}{key}")
        return lines
    lines = render_tree(tree)
    return "\n".join(lines) if lines else "No files included."
def should_include_file(file_path, config, root_dir):
    ext = Path(file_path).suffix.lower()
    relative_path = str(Path(file_path).relative_to(root_dir)).replace('\\', '/')
    has_matching_ext = ext in [e.lower() for e in config["Extensions"]]
    has_include_match = any(re.match(glob_to_regex(pattern), relative_path, re.IGNORECASE) for pattern in config["IncludePatterns"])
    if not has_matching_ext and not has_include_match:
        log_write(f"Excluded {relative_path} - No ext match and no include pattern")
        return False
    if any(re.match(glob_to_regex(pattern), relative_path, re.IGNORECASE) for pattern in config["Exclude"]):
        log_write(f"Excluded {relative_path} - Matches exclude pattern")
        return False
    log_write(f"Included {relative_path}")
    return True
def remove_comments(content, comment_regex):
    return re.sub(comment_regex, '', content, flags=re.DOTALL)
def collapse_whitespace(content):
    content = re.sub(r'\s+', ' ', content)
    return content
def minify_content(ext, content, minify=False):
    if not minify:
        return content
    ext = ext.lower()
    if ext in [".js", ".ts", ".jsx", ".tsx"]:
        if shutil.which("terser"):
            try:
                result = subprocess.run(["terser", "--compress", "--mangle"], input=content.encode(), capture_output=True, check=True)
                return result.stdout.decode()
            except Exception as e:
                log_write(f"External minifier failed for {ext}: {e}, falling back to simple minify")
        # Simple minify for JS/TS
        content = remove_comments(content, r'/\*.*?\*/')
        content = re.sub(r'//.*?(?=\n|$)', '', content)
        content = re.sub(r'^\s*//.*$', '', content, flags=re.MULTILINE)
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        content = ' '.join(lines)
        content = re.sub(r'\s*([{};,=+\-*/])\s*', r'\1', content)
        return collapse_whitespace(content)
    elif ext == ".css":
        if shutil.which("cleancss"):
            try:
                result = subprocess.run(["cleancss", "-O2"], input=content.encode(), capture_output=True, check=True)
                return result.stdout.decode()
            except Exception as e:
                log_write(f"External minifier failed for {ext}: {e}, falling back to simple minify")
        # Simple minify for CSS
        content = remove_comments(content, r'/\*.*?\*/')
        return collapse_whitespace(content)
    elif ext in [".html", ".htm"]:
        if shutil.which("html-minifier"):
            try:
                result = subprocess.run(["html-minifier", "--collapse-whitespace", "--remove-comments"], input=content.encode(), capture_output=True, check=True)
                return result.stdout.decode()
            except Exception as e:
                log_write(f"External minifier failed for {ext}: {e}, falling back to simple minify")
        # Simple minify for HTML
        content = remove_comments(content, r'<!--.*?-->')
        content = re.sub(r'>\s+<', '><', content)
        return content.strip()
    return content
def create_section_header(relative_path, is_first_part, split_part_num, format_out):
    if is_first_part:
        return f"## {relative_path}\n\n"
    else:
        return f"## Continuation of {relative_path} (Part {split_part_num})\n\n"
def add_section(sections, relative_path, current_section, split_part_num, is_first_part, is_continuation):
    section_header = create_section_header(relative_path, is_first_part, split_part_num)
    full_section = section_header + current_section + "\n"
    section_relative_path = relative_path if is_first_part else f"Continuation of {relative_path} (Part {split_part_num})"
    sections.append({
        "RelativePath": section_relative_path,
        "FileSection": full_section,
        "Length": len(full_section),
        "OriginalPath": relative_path,
        "SectionIndex": split_part_num,
        "HasContinuation": is_continuation
    })
    log_write(f"Added section {split_part_num} for {relative_path} (size: {len(full_section)})")
def split_large_file(content, relative_path, max_section_size, format_out, lang, include_hashes=False, file_hash=None, split_part_num=1, is_minify_mode=False):
    sections = []
    lines = content.splitlines(keepends=True) if content else []
    current_section = ""
    current_size = 0
    effective_max = max_section_size - 500 # Conservative allowance for header and overhead
    chunk_size = effective_max - 200
    is_first_part = True
    log_write(f"Splitting file {relative_path} into sections (max size: {max_section_size}, minifyMode: {is_minify_mode})")
    if not content or not lines:
        log_write(f"Warning: Empty content for {relative_path}, creating single empty section")
        hash_str = f" SHA256: {file_hash}" if include_hashes and file_hash else ""
        h = create_section_header(relative_path + hash_str, True, 1, format_out)
        lang_str = lang if lang else ""
        section_header = h + f"``` {lang_str}\n" if lang_str else h + f"```\n"
        code_end = "\n```\n\n"
        full_section = section_header + "" + code_end
        sections.append({
            "RelativePath": relative_path,
            "FileSection": full_section,
            "Length": len(full_section),
            "OriginalPath": relative_path,
            "SectionIndex": split_part_num,
            "HasContinuation": False
        })
        return sections
    for line_index, line in enumerate(lines):
        line_size = len(line)
        assert line_index >= 0 and line_index < len(lines), "Off-by-one in line_index"
        if line_size > effective_max:
            log_write(f"Warning: Line too long in {relative_path} at line {line_index} (size: {line_size} > {effective_max}), force chunking")
            pos = 0
            while pos < len(line):
                end_pos = min(pos + chunk_size, len(line))
                assert pos < end_pos, "Off-by-one in chunk positions"
                chunk = line[pos:end_pos]
                chunk_size_actual = len(chunk)
                more_in_line = end_pos < len(line)
                more_lines = line_index < len(lines) - 1
                has_more = more_in_line or more_lines
                if current_size + chunk_size_actual > effective_max and current_section:
                    if has_more:
                        current_section += "# [CONTINUATION_PLACEHOLDER]\n"
                    hash_str = f" SHA256: {file_hash}" if include_hashes and file_hash and is_first_part else ""
                    h = create_section_header(relative_path + hash_str if is_first_part else relative_path, is_first_part, split_part_num, format_out)
                    lang_str = lang if lang else ""
                    section_header = h + f"``` {lang_str}\n" if lang_str else h + f"```\n"
                    code_end = "\n```\n\n"
                    full_section = section_header + current_section + code_end
                    sections.append({
                        "RelativePath": relative_path if is_first_part else f"Continuation of {relative_path} (Part {split_part_num})",
                        "FileSection": full_section,
                        "Length": len(full_section),
                        "OriginalPath": relative_path,
                        "SectionIndex": split_part_num,
                        "HasContinuation": has_more
                    })
                    split_part_num += 1
                    is_first_part = False
                    current_section = chunk
                    current_size = chunk_size_actual
                else:
                    current_section += chunk
                    current_size += chunk_size_actual
                pos = end_pos
            continue
        elif not is_minify_mode and line_size > chunk_size:
            log_write(f"Warning: Long line in non-minified {relative_path} at line {line_index} (length: {len(line)}), deferring whole line to next section")
            if current_size + line_size > effective_max and current_section:
                more_lines = line_index < len(lines) - 1
                has_continuation = more_lines
                if has_continuation:
                    current_section += "# [CONTINUATION_PLACEHOLDER]\n"
                hash_str = f" SHA256: {file_hash}" if include_hashes and file_hash and is_first_part else ""
                h = create_section_header(relative_path + hash_str if is_first_part else relative_path, is_first_part, split_part_num, format_out)
                lang_str = lang if lang else ""
                section_header = h + f"``` {lang_str}\n" if lang_str else h + f"```\n"
                code_end = "\n```\n\n"
                full_section = section_header + current_section + code_end
                sections.append({
                    "RelativePath": relative_path if is_first_part else f"Continuation of {relative_path} (Part {split_part_num})",
                    "FileSection": full_section,
                    "Length": len(full_section),
                    "OriginalPath": relative_path,
                    "SectionIndex": split_part_num,
                    "HasContinuation": has_continuation
                })
                split_part_num += 1
                is_first_part = False
                current_section = line
                current_size = line_size
            else:
                current_section += line
                current_size += line_size
            continue
        else:
            if current_size + line_size > effective_max and current_section:
                more_lines = line_index < len(lines) - 1
                has_continuation = more_lines
                if has_continuation:
                    current_section += "# [CONTINUATION_PLACEHOLDER]\n"
                hash_str = f" SHA256: {file_hash}" if include_hashes and file_hash and is_first_part else ""
                h = create_section_header(relative_path + hash_str if is_first_part else relative_path, is_first_part, split_part_num, format_out)
                lang_str = lang if lang else ""
                section_header = h + f"``` {lang_str}\n" if lang_str else h + f"```\n"
                code_end = "\n```\n\n"
                full_section = section_header + current_section + code_end
                sections.append({
                    "RelativePath": relative_path if is_first_part else f"Continuation of {relative_path} (Part {split_part_num})",
                    "FileSection": full_section,
                    "Length": len(full_section),
                    "OriginalPath": relative_path,
                    "SectionIndex": split_part_num,
                    "HasContinuation": has_continuation
                })
                split_part_num += 1
                is_first_part = False
                current_section = line
                current_size = line_size
            else:
                current_section += line
                current_size += line_size
    if current_section:
        hash_str = f" SHA256: {file_hash}" if include_hashes and file_hash and is_first_part else ""
        h = create_section_header(relative_path + hash_str if is_first_part else relative_path, is_first_part, split_part_num, format_out)
        lang_str = lang if lang else ""
        section_header = h + f"``` {lang_str}\n" if lang_str else h + f"```\n"
        code_end = "\n```\n\n"
        full_section = section_header + current_section + code_end
        sections.append({
            "RelativePath": relative_path if is_first_part else f"Continuation of {relative_path} (Part {split_part_num})",
            "FileSection": full_section,
            "Length": len(full_section),
            "OriginalPath": relative_path,
            "SectionIndex": split_part_num,
            "HasContinuation": False
        })
    else:
        log_write(f"Warning: No final section created for {relative_path}")
    log_write(f"Completed splitting {relative_path} into {len(sections)} sections")
    return sections
def test_filter(start_dir, output_dir, extensions, include_patterns, exclude, exclude_cmake, exclude_vscode, input_type):
    try:
        if input_type == "GitHub":
            return "GitHub mode: Filter test requires cloning; run dump to verify.", "blue"
        if not os.path.exists(start_dir):
            raise ValueError("Start path does not exist.")
        output_full_dir = os.path.dirname(output_dir) if os.path.isfile(output_dir) else output_dir
        if not os.path.exists(output_full_dir):
            raise ValueError("Output path is invalid.")
        test_config = {"Extensions": extensions, "IncludePatterns": include_patterns, "Exclude": exclude[:]}
        cmake_patterns = ["cmake/**", "CMakeLists.txt"]
        if exclude_cmake:
            for pat in cmake_patterns:
                if pat not in test_config["Exclude"]:
                    test_config["Exclude"].append(pat)
        if exclude_vscode:
            pat = ".vscode/**"
            if pat not in test_config["Exclude"]:
                test_config["Exclude"].append(pat)
        root_for_test = os.path.dirname(start_dir) if os.path.isfile(start_dir) else start_dir
        test_files = []
        for root, dirs, files in os.walk(root_for_test):
            for file in files:
                test_files.append(os.path.join(root, file))
        filtered_files = [f for f in test_files if should_include_file(f, test_config, root_for_test)]
        included_count = len(filtered_files)
        if included_count == 0:
            message = "Directory mode: 0 file(s) would be included after filtering."
        else:
            first_few = ', '.join(os.path.basename(f) for f in filtered_files[:5]) # Use basename for cleaner output
            message = f"Directory mode: {included_count} file(s) would be included.\nFirst 5: {first_few}"
        return message, "green"
    except Exception as e:
        return f"Test error: {e}", "red"
def apply_additional_excludes(exclude, exclude_cmake, exclude_vscode):
    final_exclude = exclude[:]
    cmake_patterns = ["cmake/**", "CMakeLists.txt"]
    if exclude_cmake:
        for pat in cmake_patterns:
            if pat not in final_exclude:
                final_exclude.append(pat)
    if exclude_vscode:
        pat = ".vscode/**"
        if pat not in final_exclude:
                final_exclude.append(pat)
    return final_exclude
def apply_dynamic_patterns(include_patterns, exclude, dynamic_patterns, is_exclude_dynamic):
    final_include = include_patterns[:]
    if not is_exclude_dynamic:
        final_include += dynamic_patterns
    else:
        exclude += dynamic_patterns
    return final_include, exclude
def load_all_project_configs(project_dir):
    configs = []
    for root, _, files in os.walk(project_dir):
        if '.dump-project.json' in files:
            path = os.path.join(root, '.dump-project.json')
            try:
                with open(path, "r", encoding="utf-8") as f:
                    configs.append(json.load(f))
            except Exception as e:
                logging.error(f"Failed to load config from {path}: {e}")
    if not configs:
        return {}
    merged = {
        "Exclude": [],
        "Extensions": [],
        "IncludePatterns": [],
        "DynamicPatterns": [],
        "Presets": {},
        "UseDefaultBackupPath": True,
        "FullBackup": False,
        "IncludeBinary": False,
        "Profile": "Custom",
        "Minify": False,
        "IncludeHashes": False,
        "MaxPartSize": 19000,
        "Format": "txt",
        "SplitLargeFiles": True,
        "SingleFileLimit": 15000,
        "ExcludeCMake": True,
        "ExcludeVSCode": True,
        "IsExcludeDynamic": False,
        "UsePlaceholders": False,
        "IncludeTree": True,
        "ParseGit": True,
        "Timestamp": False,
        "MaxOutputParts": 0
    }
    for config in configs:
        for key in ["Exclude", "Extensions", "IncludePatterns", "DynamicPatterns"]:
            if key in config:
                merged[key].extend(config[key])
        if "Presets" in config:
            for preset_name, files in config["Presets"].items():
                if preset_name not in merged["Presets"]:
                    merged["Presets"][preset_name] = []
                merged["Presets"][preset_name].extend(files)
        for key in merged:
            if key not in ["Exclude", "Extensions", "IncludePatterns", "DynamicPatterns", "Presets"] and key in config:
                merged[key] = config[key] # last wins
    for key in ["Exclude", "Extensions", "IncludePatterns", "DynamicPatterns"]:
        merged[key] = list(set(merged[key]))
    for preset_name in merged["Presets"]:
        merged["Presets"][preset_name] = list(set(merged["Presets"][preset_name]))
    return merged
def load_project_config(process_dir):
    merged = load_all_project_configs(process_dir)
    return merged.get("Exclude", []), merged.get("UseDefaultBackupPath", True)
def collect_files(process_dir, dump_config, full_backup=False):
    all_files = []
    if full_backup:
        for root, dirs, files in os.walk(process_dir):
            for file in files:
                all_files.append(os.path.join(root, file))
    else:
        for root, dirs, files in os.walk(process_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if should_include_file(file_path, dump_config, process_dir):
                    all_files.append(file_path)
    return all_files
# --- Core Processing Functions Section ---
def do_backup(project_dir, dump_config, full_backup=False, use_default_backup_path=True, parse_git=True):
    project_excludes, _ = load_project_config(project_dir)
    dump_config["Exclude"].extend([p for p in project_excludes if p not in dump_config["Exclude"]])
    if parse_git and not full_backup:
        git_path = os.path.join(project_dir, '.gitignore')
        if os.path.exists(git_path):
            git_excludes = parse_gitignore(git_path)
            dump_config["Exclude"].extend([p for p in git_excludes if p not in dump_config["Exclude"]])
    all_files = collect_files(project_dir, dump_config, full_backup)
    if not all_files:
        return "No files to backup.", "red"
    project_name = os.path.basename(project_dir)
    backup_path = get_backup_path(project_dir, project_name, use_default_backup_path)
    create_archive(all_files, project_dir, backup_path)
    return f"Backup created at {backup_path}", "green"
def get_backup_path(project_dir, project_name, use_default_backup_path=True):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if py7zr:
        backup_file = f"{project_name}_{ts}.7z"
    else:
        backup_file = f"{project_name}_{ts}.zip"
    if use_default_backup_path:
        backup_dir = Path.home() / "Dev_backup"
    else:
        backup_dir = Path(project_dir) / ".backup"
    backup_dir.mkdir(exist_ok=True)
    return backup_dir / backup_file
def create_archive(all_files, project_dir, backup_path):
    if py7zr and str(backup_path).endswith('.7z'):
        with py7zr.SevenZipFile(backup_path, 'w') as z:
            for file in all_files:
                z.write(file, str(Path(file).relative_to(project_dir)))
    else:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in all_files:
                arcname = Path(file).relative_to(project_dir)
                zipf.write(file, arcname)
def _process_dump(process_dir, output_dir, output_base, minify, include_hashes, max_part_size, format_out, split_large_files, single_file_limit, extensions, include_patterns, exclude, exclude_cmake, exclude_vscode, dynamic_patterns, is_exclude_dynamic, use_placeholders, include_tree, parse_git, max_output_parts, include_binary, preset_files=None, progress_callback=None, full_backup=False):
    log_message(f"Processing directory: {process_dir}")
    log_message(f"Output directory: {output_dir}")
    log_message(f"Minify enabled: {minify}")
    log_message(f"Include hashes: {include_hashes}")
    log_message(f"Max part size: {max_part_size}")
    log_message(f"Output format: {format_out}")
    log_message(f"Split large files: {split_large_files}")
    log_message(f"Use placeholders: {use_placeholders}")
    log_message(f"Single file limit: {single_file_limit}")
    log_message(f"Include tree: {include_tree}")
    log_message(f"Parse .gitignore: {parse_git}")
    log_message(f"Max output parts: {max_output_parts}")
    log_message(f"Include binary: {include_binary}")
    log_message(f"Full backup: {full_backup}")
    if progress_callback:
        progress_callback(f"Processing directory: {process_dir}", "blue")
    if not os.path.exists(process_dir):
        log_message(f"Error: Directory {process_dir} does not exist")
        return "Directory does not exist", "red"
    # Apply additional excludes
    exclude = apply_additional_excludes(exclude, exclude_cmake, exclude_vscode)
    # Apply dynamic patterns
    include_patterns, exclude = apply_dynamic_patterns(include_patterns, exclude, dynamic_patterns, is_exclude_dynamic)
    # Load project-specific exclusions
    project_excludes, use_default_backup_path = load_project_config(process_dir)
    exclude.extend([p for p in project_excludes if p not in exclude])
    if project_excludes:
        log_message(f"Added {len(project_excludes)} project-specific exclude patterns")
    # Parse .gitignore if enabled
    if parse_git and not full_backup:
        git_path = os.path.join(process_dir, '.gitignore')
        if os.path.exists(git_path):
            git_excludes = parse_gitignore(git_path)
            exclude.extend([p for p in git_excludes if p not in exclude])
            log_message(f"Added {len(git_excludes)} patterns from .gitignore")
    dump_config = {"Extensions": extensions, "IncludePatterns": include_patterns, "Exclude": exclude}
    all_files = []
    if preset_files:
        all_files = [f for f in preset_files if os.path.exists(f)]
        log_message(f"Using preset with {len(all_files)} files")
    else:
        all_files = collect_files(process_dir, dump_config, full_backup)
    log_message(f"Found {len(all_files)} files after filtering")
    # Build tree if requested
    tree_section = ""
    if include_tree:
        tree_str = build_tree_from_files(all_files, process_dir)
        tree_section = f"## Project Structure\n\n```\n{tree_str}\n```\n\n"
        log_message("Project tree generated")
    file_items = []
    total_files = len(all_files)
    ignore_size_limits = max_output_parts > 0
    if ignore_size_limits:
        split_large_files = False
        use_placeholders = False
    for current_file_index, file_path in enumerate(all_files, 1):
        percent_complete = round((current_file_index / total_files) * 100)
        log_message(f"Processing file {current_file_index}/{total_files} ({percent_complete}%)")
        if progress_callback:
            progress_callback(f"Processing file {current_file_index}/{total_files} ({percent_complete}%)", "blue")
        try:
            ext = Path(file_path).suffix
            relative_path = os.path.relpath(file_path, process_dir).replace('\\', '/')
            minify_mode_for_split = minify and ext.lower() in [".js", ".ts", ".jsx", ".tsx", ".css", ".html", ".htm"]
            file_hash = None
            if include_hashes:
                with open(file_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    original_content = f.read()
                content = original_content
                if ext in [".js", ".ts", ".jsx", ".tsx", ".css", ".html", ".htm"]:
                    content = minify_content(ext, content, minify)
                    log_message(f"Processed {relative_path} (minify={minify})")
                is_binary = False
            except UnicodeDecodeError:
                if not include_binary:
                    log_message(f"Skipping binary file {relative_path}")
                    continue
                with open(file_path, "rb") as f:
                    content = f.read()
                content = base64.b64encode(content).decode('utf-8')
                is_binary = True
                log_message(f"Encoded binary file {relative_path} as base64")
            lang = ext_to_lang.get(ext.lower(), "text") if not is_binary else "base64"
            original_size = len(original_content) if not is_binary else len(content)
            hash_str = f" SHA256: {file_hash}" if include_hashes and file_hash else ""
            header = f"## {relative_path}{hash_str}\n"
            lang_str = lang if lang else ""
            section_header = header + f"``` {lang_str}\n" if lang_str else header + f"```\n"
            code_end = "\n```\n\n"
            file_section = section_header + content + code_end
            section_length = len(file_section)
            if not ignore_size_limits:
                if use_placeholders and section_length > single_file_limit:
                    placeholder_section = header + f"Large file ({original_size} characters). Content omitted to optimize for AI context.\n\n"
                    section_length = len(placeholder_section)
                    file_items.append({
                        "RelativePath": relative_path,
                        "FileSection": placeholder_section,
                        "Length": section_length,
                        "OriginalPath": relative_path,
                        "SectionIndex": 1,
                        "HasContinuation": False
                    })
                    log_message(f"Added placeholder for large file {relative_path} (size: {original_size})")
                elif split_large_files and section_length > single_file_limit:
                    log_message(f"Splitting large file {relative_path} (size: {section_length})")
                    split_sections = split_large_file(content, relative_path, single_file_limit, format_out, lang, include_hashes, file_hash, 1, minify_mode_for_split)
                    for sec in split_sections:
                        log_message(f"Added split section {sec['RelativePath']} (size: {sec['Length']})")
                    file_items.extend(split_sections)
                else:
                    if section_length > max_part_size:
                        log_message(f"Warning: File {relative_path} exceeds max part size ({section_length} > {max_part_size}), skipping")
                        continue
                    file_items.append({
                        "RelativePath": relative_path,
                        "FileSection": file_section,
                        "Length": section_length,
                        "OriginalPath": relative_path,
                        "SectionIndex": 1,
                        "HasContinuation": False
                    })
                    log_message(f"Added non-split file {relative_path} (size: {section_length})")
            else:
                file_items.append({
                    "RelativePath": relative_path,
                    "FileSection": file_section,
                    "Length": section_length,
                    "OriginalPath": relative_path,
                    "SectionIndex": 1,
                    "HasContinuation": False
                })
                log_message(f"Added full file {relative_path} (size: {section_length}) ignoring size limits")
        except Exception as e:
            log_message(f"Error processing {file_path}: {e}")
    # Sort file_items
    file_items.sort(key=lambda x: (x["OriginalPath"], x["SectionIndex"]))
    log_message("Queue before packing:")
    for item in file_items:
        log_message(f" - {item['RelativePath']} (size: {item['Length']}, SectionIndex: {item['SectionIndex']})")
    # Prepare for packing with effective lengths to account for TOC and tree
    base_length = len(f"# Project File Dump (Part 1)\n\nThis file contains a dump of relevant project files (Part 1).\n\n") + 200 # Base header + margin
    tree_len = len(tree_section) if include_tree else 0
    toc_per_item = 50 # Estimate for TOC lines
    for item in file_items:
        item["EffectiveLength"] = item["Length"] + toc_per_item
    # Filter out items too large for any part (only if not ignoring sizes)
    if not ignore_size_limits:
        file_items = [item for item in file_items if item["Length"] <= max_part_size - base_length - 1000]
    # First-Fit Decreasing bin packing, with max_output_parts limit
    parts = [] # list of (current_effective, list_of_items)
    sorted_items = sorted(file_items, key=lambda x: x["EffectiveLength"], reverse=True)
    is_first_part = True
    if max_output_parts > 0:
        # Force into max_output_parts bins, even if over size (ignore size limits)
        parts = [(0, []) for _ in range(max_output_parts)]
        for item in sorted_items:
            # Find bin with smallest current length
            min_bin = min(range(max_output_parts), key=lambda i: parts[i][0])
            cl, clist = parts[min_bin]
            parts[min_bin] = (cl + item["EffectiveLength"], clist + [item])
    else:
        for item in sorted_items:
            placed = False
            for i in range(len(parts)):
                cl, clist = parts[i]
                effective_max = max_part_size - (tree_len if i == 0 and include_tree else 0)
                if cl + item["EffectiveLength"] <= effective_max:
                    parts[i] = (cl + item["EffectiveLength"], clist + [item])
                    placed = True
                    break
            if not placed:
                base = base_length + (tree_len if is_first_part and include_tree else 0)
                parts.append((base + item["EffectiveLength"], [item]))
                is_first_part = False
    # Assign part numbers
    for part_num, (cl, part) in enumerate(parts, 1):
        for item in part:
            item["PartNumber"] = part_num
    # Update continuations
    log_message("Updating continuation placeholders:")
    grouped = defaultdict(list)
    for item in file_items:
        grouped[item["OriginalPath"]].append(item)
    for orig, group in grouped.items():
        group.sort(key=lambda x: x["SectionIndex"])
        if len(group) > 1:
            for i in range(len(group) - 1):
                current = group[i]
                next_item = group[i + 1]
                next_part = next_item["PartNumber"]
                if current["HasContinuation"]:
                    placeholder_pattern = re.compile(r'^# \[CONTINUATION_PLACEHOLDER\]$', re.MULTILINE)
                    new_note = f"# {orig} continues in part {next_part}"
                    current["FileSection"] = placeholder_pattern.sub(new_note, current["FileSection"])
                    log_message(f"Updated placeholder for {orig} section {current['SectionIndex']} to point to part {next_part}")
    all_files_summary = list(set(item["OriginalPath"] for item in file_items))
    log_message("Final parts:")
    for p, (cl, part) in enumerate(parts, 1):
        log_message(f"Part {p}: {len(part)} items (total size: {cl})")
        for item in part:
            log_message(f" - {item['RelativePath']} (size: {item['Length']}, PartNumber: {item['PartNumber']})")
    os.makedirs(output_dir, exist_ok=True)
    base_header = f"# Project File Dump (Part {{0}})\n\nThis file contains a dump of relevant project files (Part {{0}}).\n\n"
    ext = "." + format_out
    for part_num, (cl, part) in enumerate(parts, 1):
        current_content = base_header.format(part_num)
        if include_tree and part_num == 1:
            current_content += tree_section
        toc = "## Files in this Part\n\n"
        for item in part:
            toc += f"- {item['RelativePath']}\n"
        toc += "\n"
        current_content += toc
        for item in part:
            current_content += item["FileSection"]
        output_path = os.path.join(output_dir, f"{output_base}-part-{part_num}{ext}")
        log_message(f"Writing to: {output_path}")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(current_content)
        log_message(f"Project dump part {part_num} written to {output_path} with {len(part)} files/sections")
    if not parts:
        output_path = os.path.join(output_dir, f"{output_base}-part-1{ext}")
        log_message(f"Writing empty dump to: {output_path}")
        empty_content = "# Project File Dump (Part 1)\n\nNo relevant project files found.\n"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(empty_content)
    if parts:
        summary_path = os.path.join(output_dir, f"{output_base}-summary.md")
        summary_content = "# Project Dump Summary\n\n"
        summary_content += f"## Total Files: {len(all_files_summary)}\n"
        summary_content += f"## Total Parts: {len(parts)}\n\n"
        if include_tree:
            summary_content += tree_section
        summary_content += "## Files by Part\n\n"
        for p in range(1, len(parts) + 1):
            summary_content += f"### Part {p}\n"
            part_items = [item for item in file_items if item.get("PartNumber") == p]
            for item in part_items:
                summary_content += f"- [{item['RelativePath']}]({output_base}-part-{p}{ext})\n"
            summary_content += "\n"
        summary_content += "## All Files\n\n"
        for f in sorted(all_files_summary):
            summary_content += f"- {f}\n"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_content)
        log_message(f"Summary written to: {summary_path}")
    log_message(f"Script completed successfully. Total parts: {len(parts)}")
    return f"Completed! Check {log_path} for details. Output in {output_dir}.", "green"
def run_dump(start_dir, output_dir, output_base, minify, include_hashes, max_part_size, format_out, split_large_files, single_file_limit, extensions, include_patterns, exclude, exclude_cmake, exclude_vscode, dynamic_patterns, is_exclude_dynamic, input_type, use_placeholders, include_tree, parse_git, timestamp, max_output_parts, include_binary=False, preset_files=None, progress_callback=None, full_backup=False):
    original_input = start_dir
    project_root = None
    if timestamp:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_base = f"{output_base}_{ts}"
        log_message(f"Added timestamp to output base: {output_base}")
    is_single_file_input = os.path.isfile(start_dir) if input_type == "Local" else False
    if input_type == "Local":
        # By design, when input is a file, use its parent directory as the project root. This ensures the script processes the containing project.
        project_root = os.path.dirname(start_dir) if is_single_file_input else start_dir
    if input_type == "GitHub":
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                subprocess.check_call(["git", "clone", "--depth=1", start_dir, "."], cwd=temp_dir, capture_output=True, check=True)
                process_dir = temp_dir
                log_message(f"Cloned GitHub repo to temp dir: {process_dir}")
                return _process_dump(process_dir, output_dir, output_base, minify, include_hashes, max_part_size, format_out, split_large_files, single_file_limit, extensions, include_patterns, exclude, exclude_cmake, exclude_vscode, dynamic_patterns, is_exclude_dynamic, use_placeholders, include_tree, parse_git, max_output_parts, include_binary, preset_files, progress_callback, full_backup)
            except subprocess.CalledProcessError as e:
                log_message(f"Git clone failed: {e}")
                return "Failed to clone GitHub repository.", "red"
            except Exception as e:
                log_message(f"Error handling GitHub input: {e}")
                return f"Error with GitHub input: {e}", "red"
    else:
        # Local
        process_dir = project_root
        output_dir = os.path.abspath(output_dir)
        if project_root and (output_dir == os.getcwd() or output_dir == os.path.abspath(original_input)):
            output_dir = os.path.abspath(process_dir)
        return _process_dump(process_dir, output_dir, output_base, minify, include_hashes, max_part_size, format_out, split_large_files, single_file_limit, extensions, include_patterns, exclude, exclude_cmake, exclude_vscode, dynamic_patterns, is_exclude_dynamic, use_placeholders, include_tree, parse_git, max_output_parts, include_binary, preset_files, progress_callback, full_backup)
def cli_run(args):
    # Construct params from args and custom_config (updated in main for profiles)
    start_dir = args.input if args.input is not None else os.getcwd()
    output_dir = None
    output_base = args.output_base
    if args.output:
        if os.path.isdir(args.output):
            output_dir = args.output
        else:
            output_dir = os.path.dirname(os.path.abspath(args.output))
            output_base = os.path.splitext(os.path.basename(args.output))[0]
    if output_dir is None:
        if os.path.isfile(start_dir):
            output_dir = os.path.dirname(start_dir)
        else:
            output_dir = start_dir
    if not args.output_base:
        project_dir = os.path.dirname(start_dir) if os.path.isfile(start_dir) else start_dir
        output_base = os.path.basename(project_dir)
    extensions = parse_extensions(args.extensions) if args.extensions else custom_config.get("Extensions", default_profiles["Custom"]["Extensions"])
    include_patterns = parse_list(args.include) if args.include else custom_config.get("IncludePatterns", [])
    exclude = parse_list(args.exclude) if args.exclude else custom_config.get("Exclude", default_profiles["Custom"]["Exclude"])
    split_large_files = not args.no_split
    preset_files = None
    if args.preset:
        project_dir = os.path.dirname(start_dir) if os.path.isfile(start_dir) else start_dir
        merged = load_all_project_configs(project_dir)
        presets = merged.get("Presets", {})
        if args.preset not in presets:
            raise ValueError(f"Preset '{args.preset}' not found in project config.")
        preset_files = [os.path.join(project_dir, rel.replace('/', os.sep)) for rel in presets[args.preset]]
    if args.backup:
        if args.input_type == "GitHub":
            print("Backup not supported for GitHub input.")
            return 1
        project_dir = os.path.dirname(start_dir) if os.path.isfile(start_dir) else start_dir
        dump_config = {"Extensions": extensions, "IncludePatterns": include_patterns, "Exclude": exclude}
        message, color = do_backup(project_dir, dump_config, args.full_backup, default_use_default_backup_path, args.parse_git)
        print(message)
        return 0 if "created" in message.lower() else 1
    try:
        message, color = run_dump(
            start_dir=start_dir,
            output_dir=output_dir,
            output_base=output_base,
            minify=args.minify,
            include_hashes=args.hashes,
            max_part_size=args.max_part_size,
            format_out=args.format,
            split_large_files=split_large_files,
            single_file_limit=args.single_file_limit,
            extensions=extensions,
            include_patterns=include_patterns,
            exclude=exclude,
            exclude_cmake=True, # default
            exclude_vscode=True, # default
            dynamic_patterns=[], # no CLI support
            is_exclude_dynamic=False,
            input_type=args.input_type,
            use_placeholders=args.use_placeholders,
            include_tree=args.include_tree,
            parse_git=args.parse_git,
            timestamp=args.timestamp,
            max_output_parts=args.max_output_parts,
            include_binary=args.include_binary,
            preset_files=preset_files,
            full_backup=args.full_backup
        )
    except ValueError as e:
        print(f"Error in CLI: {e}")
        return 1
    print(message)
    return 0 if "Completed" in message else 1
def save_config(custom_config):
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(custom_config, f, indent=4)
# TODO (Major Enhancement): Add support for more input types like local Git repos or zip archives.
# TODO (Major Enhancement): Add CLI support for GitHub input (--input-type github URL).
# TODO (Major Enhancement): Support custom minification plugins or scripts.
# TODO (Major Enhancement): Allow overriding default profile deletion with confirmation for advanced users.
# TODO (Major Enhancement): Load profiles from external files for easier sharing/updates.
# TODO: Make backup interval configurable in GUI and CLI.