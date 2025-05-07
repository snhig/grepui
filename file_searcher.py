import argparse, re
from pathlib import Path
import sys
 
def find_files(root_dir: Path, extension: str, search_string: str, use_regex=False, recursive=True, case_insensitive=True):
    results = []

    if use_regex:
        flags = re.IGNORECASE if case_insensitive else 0
        pattern = re.compile(search_string, flags)
    else:
        pattern = search_string.lower() if case_insensitive else search_string

    globber = root_dir.rglob if recursive else root_dir.glob

    for file_path in globber(f"*{extension}"):
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                match_count = 0
                for line in f:
                    if use_regex:
                        match_count += len(pattern.findall(line))
                    else:
                        haystack = line.lower() if case_insensitive else line
                        match_count += haystack.count(pattern)
                if match_count > 0:
                    results.append((file_path, match_count))
        except Exception as e:
            print(f"Warning: could not read {file_path}: {e}", file=sys.stderr)

    return results


 
def main():
    parser = argparse.ArgumentParser(
        description="Recursively search for a string in all files of a given extension."
    )
    parser.add_argument(
        "root_dir",
        type=Path,
        help="Path to the directory you want to search"
    )
    parser.add_argument(
        "extension",
        help="File extension to include in search (e.g. .py, .txt)"
    )
    parser.add_argument(
        "search_string",
        help="Exact substring to look for in the files"
    )
    args = parser.parse_args()
 
    if not args.root_dir.is_dir():
        print(f"Error: {args.root_dir} is not a directory.", file=sys.stderr)
        sys.exit(1)
 
    matches = find_files(args.root_dir, args.extension, args.search_string)
    if matches:
        print(f"\n{len(matches)} "+"Files containing “{}”:".format(args.search_string))
        for path in matches:
            print(f'"{path}"', end=' ')
    else:
        print(f"No files with extension '{args.extension}' contain “{args.search_string}”.")
 
if __name__ == "__main__":
    main()