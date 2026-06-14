import json
import os
import sys
import base64
import requests

def download(username: str, repo: str):
    # Added 'f' for f-string and assumed 'main' branch
    url = f"https://raw.githubusercontent.com/{username}/{repo}/main/{repo}.gmbdf"
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise error for bad responses (404, 500, etc)
        return response.text
    except requests.RequestException as e:
        print(f"Error downloading package: {e}")
        return None

VERSION = "v1.1"
# Safer path construction using os.path
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
GLOBAL_PACKAGE_DIR = os.path.join(BASE_PATH, "unpacked-packages", VERSION) + "/"
DOWNLOADS_DIR = "download/"

HELP_MENU = f"""
GMBM (GameMage's Build Manager) Version {VERSION}.
Packages located at {GLOBAL_PACKAGE_DIR}

Commands:

- `help`                                                 : Shows the help menu.
- `unpack <filepath> <name>`                             : Unpacks a .gmbdf file.
- `download <user> <repo>`                               : Downloads a .gmbdf file from GitHub.
- `launch <name>`                                        : Launches a package.
- `pack <directory> [ignore-extensions] [ignore-files]`  : Packs a project (lists separated by `;`)

Note: A project must contain __entry__.py to be launched via CLI.
"""

def unpack_package(filepath: str, package_name: str):
    PACKAGE_DIR = os.path.join(GLOBAL_PACKAGE_DIR, package_name) + "/"

    if not os.path.exists(filepath):
        print(f"Error: Archive file '{filepath}' not found.")
        return

    # exist_ok=True prevents crashes if directory already exists
    os.makedirs(PACKAGE_DIR, exist_ok=True)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    
        for directory in data.get("dirs", []):
            os.makedirs(os.path.join(PACKAGE_DIR, directory), exist_ok=True)
        
        files_dict = data.get("files", {})
        for i, (filename, encoded_content) in enumerate(files_dict.items()):
            try:
                real_cont = base64.b64decode(encoded_content)
                
                # Ensure the target directory for the file exists
                target_file_path = os.path.join(PACKAGE_DIR, filename)
                os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

                with open(target_file_path, "wb") as f:
                    f.write(real_cont)
                print(f"Written file {i + 1}/{len(files_dict)}: {filename}")
            except Exception as file_err:
                print(f"Failed to write file {filename}: {file_err}")

    except Exception as e:
        print(f"Unpack aborted due to error: {e}")

def search_dir(current_dir: str, ignore_ext: list[str], ignore_files: list[str]):
    dir_dict = {}
    try:
        files_inside = os.listdir(current_dir)
    except Exception as e:
        print(f"Could not read directory {current_dir}: {e}")
        return dir_dict

    for file in files_inside:
        full_path = os.path.join(current_dir, file).replace("\\", "/")

        if file in ignore_files:
            continue
        elif os.path.isdir(full_path):
            dir_dict[file] = search_dir(full_path, ignore_ext, ignore_files)
        elif not any(file.endswith(ext) for ext in ignore_ext if ext):
            try:
                with open(full_path, "rb") as f:
                    dir_dict[file] = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"Could not read file {full_path}: {e}")
    
    return dir_dict

def collect_all_files(tree, prefix, files: dict[str, str], needed_dirs: list[str]):
    for n in tree:
        f = tree[n]
        if isinstance(f, dict):
            needed_dirs.append(prefix + n)
            collect_all_files(f, prefix + n + "/", files, needed_dirs)
        else:
            files[prefix + n] = f

def build(path: str, ignore_extensions: list[str], ignore_files: list[str]):
    loaded_files = {}
    needed_dirs = []

    tree = search_dir(path, ignore_extensions, ignore_files)
    collect_all_files(tree, "", loaded_files, needed_dirs)
    
    build_obj = {
        "dirs": needed_dirs,
        "files": loaded_files,
    }

    output_filename = os.path.join(os.path.dirname(path.rstrip("/\\")), "town_build.gmbdf")
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(build_obj, f, indent=2) # indent=2 makes debugging the json easier
    print(f"Successfully created archive at: {output_filename}")

def pack_directory(directory: str, ign_ext: str = "", ign_files: str = "", *args):
    if not os.path.isdir(directory):
        print("That's not a valid directory.")
        return
    
    # Strip empty entries resulting from splitting empty strings
    ext_list = [e for e in ign_ext.split(";") if e]
    file_list = [f for f in ign_files.split(";") if f]
    
    build(directory, ext_list, file_list)

def process_command(cmd: str):
    # Splits by spaces but protects arguments if they are formatted cleanly
    parts = [p for p in cmd.split(" ") if p]
    if not parts:
        return

    cmd_name = parts[0].lower()

    match cmd_name:
        case "help":
            print(HELP_MENU)
        case "unpack":
            if len(parts) == 3:
                print("Starting unpack process ...")
                unpack_package(parts[1], parts[2])
                print("Unpack process finished.")
            else:
                print("Usage: unpack <filepath> <name>")
        case "download":
            if len(parts) == 3:
                print(f"Downloading package from {parts[1]}...")
                text_cont = download(parts[1], parts[2])
                
                if text_cont:
                    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
                    dest_path = os.path.join(DOWNLOADS_DIR, f"{parts[2]}.gmbdf")
                    with open(dest_path, "w", encoding="utf-8") as f:
                        f.write(text_cont)
                    print(f"Saved downloaded package to {dest_path}")
            else:
                print("Usage: download <user> <repo>")
        case "launch":
            if len(parts) == 2:
                entry_point = os.path.join(GLOBAL_PACKAGE_DIR, parts[1], "__entry__.py")
                if os.path.exists(entry_point):
                    command = f'{sys.executable} "{entry_point}"'
                    print("OS Run > " + command)
                    os.system(command)
                else:
                    print(f"Error: Entry point file micro-package structural layout failed. File not found: {entry_point}")
            else:
                print("Usage: launch <name>")
        case "pack":
            if len(parts) >= 2:
                pack_directory(*parts[1:])
            else:
                print("Usage: pack <directory> [ignore-extensions] [ignore-files]")
        case _:
            print(f"Unknown command: '{cmd_name}'. Type 'help' for available options.")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(f"Welcome to the GMBM CLI, Version {VERSION}.")
        print("A package manager made in Python.")

        while True:
            try:
                cmd = input("GMBM >>> ").strip()
                if cmd.lower() in ["exit", "quit"]:
                    break
                process_command(cmd)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting GMBM.")
                break
