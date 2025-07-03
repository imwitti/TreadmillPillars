import os

# Define the file extensions to include
INCLUDED_EXTENSIONS = {'.json', '.py', '.css', '.js', '.html'}

def write_directory_contents(output_file, current_path, indent_level=0):
    indent = '    ' * indent_level
    try:
        entries = sorted(os.listdir(current_path))
    except PermissionError:
        output_file.write(f"{indent}[Permission Denied]: {current_path}\n")
        return

    for entry in entries:
        full_path = os.path.join(current_path, entry)
        if os.path.isdir(full_path):
            output_file.write(f"{indent}[Folder] {entry}/\n")
            write_directory_contents(output_file, full_path, indent_level + 1)
        elif os.path.isfile(full_path):
            _, ext = os.path.splitext(entry)
            if ext.lower() in INCLUDED_EXTENSIONS:
                output_file.write(f"{indent}[File] {entry}\n")
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as file:
                        content = file.read()
                        output_file.write(f"{indent}--- Start of {entry} ---\n")
                        for line in content.splitlines():
                            output_file.write(f"{indent}{line}\n")
                        output_file.write(f"{indent}--- End of {entry} ---\n\n")
                except Exception as e:
                    output_file.write(f"{indent}[Error reading file]: {e}\n")

def main():
    output_filename = 'directory_contents.txt'
    with open(output_filename, 'w', encoding='utf-8') as output_file:
        start_path = os.getcwd()
        output_file.write(f"Directory structure and file contents of: {start_path}\n\n")
        write_directory_contents(output_file, start_path)

if __name__ == "__main__":
    main()
