import json
import os
import sys
import base64


VERSION = "v1.0"
GLOBAL_PACKAGE_DIR = f"{"/".join(__file__.replace("\\", "/").split("/")[:-1])}/unpacked-packages/%s/" % VERSION


HELP_MENU = f"""
GMBM (GameMage's Build Manager) Version {VERSION}.
Packages located at {GLOBAL_PACKAGE_DIR}

Commands:

- help                                                                          : Shows the help menu.
- unpack <filepath> <name>                                                      : Unpacks a .gmbdf file (GameMage's Build Data File).
- unpack-git <filepath> <name>                                                  : Unpacks a .gmbdf file (GameMage's Build Data File).
- launch <name>                                                                 : Launches a package.
- pack <directory> [ignore-extensions] [ingnore-files]                          : Packs a project, both optional arguments are lists separated by `;`

Note, that a project must contain __entry__.py to be launched by the GMBM CLI launch command.
"""


def unpack_package(filepath: str, package_name: str):
    PACKAGE_DIR = GLOBAL_PACKAGE_DIR + package_name + "/"

    data = {
        "dirs": [],
        "files": {},
    }

    try:
        os.makedirs(PACKAGE_DIR)
    except:
        print("Could not make the folder, package might be already downloaded.")
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    
        for dir in data["dirs"]:
            os.makedirs(PACKAGE_DIR + dir)
        
        for i, file in enumerate(data["files"]):
            cont: str = data["files"][file]

            real_cont = base64.b64decode(cont)

            print(f"Written file {i + 1}/{len(data["files"])}")

            with open(PACKAGE_DIR + file, "wb") as f:
                f.write(real_cont)

    except Exception as e:
        print(e)

def search_dir(dir: str, ignore_files: list[str], ignore_exp: list[str]):
    dir_dict: dict[str, dict | bytes] = {}

    files_inside = os.listdir(dir)

    for file in files_inside:
        full_path = dir + "/" + file

        if file in ignore_exp:
            continue
        elif os.path.isdir(full_path):
            dir_dict[file] = search_dir(full_path, ignore_files, ignore_exp)
        elif not any([file.endswith(endfix) for endfix in ignore_files]):
            with open(full_path, "rb") as f:
                dir_dict[file] = base64.b64encode(f.read()).decode('utf-8')
    
    return dir_dict
    

def get_tree_str(root_name: str, tree):
    r = "%s/ (%d sub)" % (root_name, len(tree))

    for n in tree:
        f = tree[n]

        if isinstance(f, dict):
            r += "\n\t" + get_tree_str(n, f).replace("\n", "\n\t")
        else:
            r += "\n\t%s (%d chars)" % (n, len(f))
    
    return r


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

    """
    print(f"{" NEEDED DIRECTORIES ":-^{42 * 4}}")

    for i, d in enumerate(needed_dirs):
        print(f"| {d:<40} ", end="")
        if (i + 1) % 4 == 0:
            print("|")

    print(f"{" FILES ":-^{42 * 4}}")

    for i, k in enumerate(loaded_files):
        print(f"| {k:<40} ", end="")
        if (i + 1) % 4 == 0:
            print("|")
    print("|")
    """
    
    build_obj = {
        "dirs": needed_dirs,
        "files": loaded_files,
    }

    with open("/".join(path.replace("\\", "/").split("/")[:-1]) + "/" + "town_build.gmbdf", "w", encoding="utf-8") as f:
        json.dump(build_obj, f)

def pack_directory(dir: str, ign_ext: str = "", ign_files: str = "", *args):
    if not os.path.isdir(dir):
        print("That's not a directory.")
        return
    
    build(dir, ign_ext.split(";"), ign_files.split(";"))

def process_command(cmd: str):
    parts = cmd.split(" ")

    print(parts)

    if len(parts) > 0:
        cmd_name = parts[0].lower()

        match cmd_name:
            case "help":
                print(HELP_MENU)
            case "unpack":
                if len(parts) == 3:
                    print("Starting unpack process ...")
                    unpack_package(parts[1], parts[2])
                    print("Unpack process finished.")
            case "unpack-git":
                if len(parts) == 3:
                    print("Starting unpack process ...")
                    unpack_package(parts[1], parts[2])
                    print("Unpack process finished.")
            case "launch":
                if len(parts) == 2:
                    command = f"{sys.orig_argv[0]} {GLOBAL_PACKAGE_DIR + parts[1]}/__entry__.py"
                    print("OS > " + command)
                    os.system(command)
            case "pack":
                if len(parts) > 1:
                    pack_directory(*parts[1:])


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Welcome to the GMBM CLI, Version %s." % VERSION)
        print("A package manager made in Python.")

        while True:
            cmd = input("GMBM >>> ").strip()
            process_command(cmd)
