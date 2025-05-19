# updated: 2025-04-22 14:33:40
# created: 2024-07-19 13:40:15
# filename: insert_datetime.py
#------------------------------------------------------
import sys
from datetime import datetime
from os.path import basename
#------------------------------------------------------
def insert_datetime_label(file_path):
    # Read the current content of the file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Prepare current labels
    now = datetime.now()
    updated_label = f"# updated: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
    created_label = f"# created: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
    filename_label = f"# filename: {basename(file_path)}\n"

    # Check if each label exists
    updated_exists = any(line.startswith("# updated:") for line in lines)
    created_exists = any(line.startswith("# created:") for line in lines)
    filename_exists = any(line.startswith("# filename:") for line in lines)

    # Remove old updated label
    if updated_exists:
        lines = [line for line in lines if not line.startswith("# updated:")]

    # Insert labels at the top (in reverse desired order)
    if not filename_exists:
        lines.insert(0, filename_label)
    if not created_exists:
        lines.insert(0, created_label)
    lines.insert(0, updated_label)

    # Write changes
    with open(file_path, 'w') as file:
        file.writelines(lines)
#------------------------------------------------------
def update_program_timestamp(file_path):
    # Read the current content of the file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    now = datetime.now()
    program_updated_value = f'"{now.strftime("%Y-%m-%d %H:%M:%S")}"\n'

    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith("program_updated ="):
            leading_whitespace = line[:line.find("program_updated")]
            lines[i] = f'{leading_whitespace}program_updated = {program_updated_value}'
            updated = True
            break

    if not updated:
        lines.append(f'program_updated = {program_updated_value}')

    with open(file_path, 'w') as file:
        file.writelines(lines)
#------------------------------------------------------
if __name__ == "__main__":
    file_path = sys.argv[1]

    insert_datetime_label(file_path)

    if "main.py" in file_path or file_path.endswith(".json"):
        update_program_timestamp(file_path)
#------------------------------------------------------
