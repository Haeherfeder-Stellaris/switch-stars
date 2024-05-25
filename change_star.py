import re
import os
import zipfile
import shutil

def extract_sav_file(filename: str):
    # Extract the .sav file
    with zipfile.ZipFile(sav_file, 'r') as zip_ref:
        zip_ref.extractall('.')
    
    gamestate_file = 'gamestate'
    meta_file = 'meta'
    
    if not os.path.exists(gamestate_file) or not os.path.exists(meta_file):
        print("Extraction failed or files not found.")
        return None, None, None

    return sav_file, gamestate_file, meta_file

def extract_galactic_object_section(input_file, output_file):
    start_marker = 'galactic_object='
    start_found = False
    bracket_depth = 0
    output_lines = []

    with open(input_file, 'r') as infile:
        for line in infile:
            if not start_found:
                if line.strip() == start_marker:
                    start_found = True
                    bracket_depth += line.count('{') - line.count('}')
                    output_lines.append(line)
            else:
                output_lines.append(line)
                bracket_depth += line.count('{') - line.count('}')
                if bracket_depth == 0:
                    break

    with open(output_file, 'w') as outfile:
        outfile.writelines(output_lines)

def read_file(file_path):
    with open(file_path, 'r') as file:
        data = file.read()
    return data

def find_object(data, obj_id):
    pattern = rf'\t{obj_id}=\s*{{.*?^\t}}'
    match = re.search(pattern, data, re.DOTALL | re.MULTILINE)
    if match and match.group().count('{') == match.group().count('}'):
        return match.group(), match.start(), match.end()
    return None, None, None

def swap_coordinates(obj1, obj2):
    coord_pattern = re.compile(r'coordinate=\s*{[^{}]*({[^{}]*}[^{}]*)*}', re.DOTALL)
    coord1 = coord_pattern.search(obj1).group()
    coord2 = coord_pattern.search(obj2).group()
    obj1 = coord_pattern.sub(coord2, obj1)
    obj2 = coord_pattern.sub(coord1, obj2)
    return obj1, obj2

def swap_hyperlanes(obj1, obj2, id1, id2):
    hyperlane_pattern = re.compile(r'hyperlane=\s*{[^{}]*({[^{}]*}[^{}]*)*}', re.DOTALL)
    hyper1 = hyperlane_pattern.search(obj1)
    hyper2 = hyperlane_pattern.search(obj2)
    
    if not hyper1 or not hyper2:
        raise ValueError("One or both hyperlane objects not found.")
    
    hyper1 = hyper1.group()
    hyper2 = hyper2.group()

    hyper1 = re.sub(rf'\bto={id1}\b', f'to={id2}', hyper1)
    hyper2 = re.sub(rf'\bto={id2}\b', f'to={id1}', hyper2)

    obj1 = hyperlane_pattern.sub(hyper2, obj1)
    obj2 = hyperlane_pattern.sub(hyper1, obj2)

    return obj1, obj2

def update_references(data, id1, id2):
    updated_data = re.sub(rf'\bto={id1}\b', f'to=TEMP_ID', data)
    updated_data = re.sub(rf'\bto={id2}\b', f'to={id1}', updated_data)
    updated_data = re.sub(rf'\bto=TEMP_ID\b', f'to={id2}', updated_data)
    return updated_data

def write_file(file_path, data):
    with open(file_path, 'w') as file:
        file.write(data)

def main_process(input_file_path, output_file_path):
    data = read_file(input_file_path)

    swaps = []
    while True:
        id1 = input("Enter the first object ID: ")
        id2 = input("Enter the second object ID: ")
        swaps.append((id1, id2))
        another_swap = input("Do you want to swap another pair of objects? (yes/no): ")
        if another_swap.lower() != 'yes':
            break

    for id1, id2 in swaps:
        obj1, start1, end1 = find_object(data, id1)
        obj2, start2, end2 = find_object(data, id2)

        if not obj1 or not obj2:
            print(f"One or both object IDs not found for pair ({id1}, {id2}). Skipping this pair.")
            continue

        obj1, obj2 = swap_coordinates(obj1, obj2)

        try:
            obj1, obj2 = swap_hyperlanes(obj1, obj2, id1, id2)
        except ValueError as e:
            print(e)
            continue

        if start1 < start2:
            data = data[:start1] + obj1 + data[end1:start2] + obj2 + data[end2:]
        else:
            data = data[:start2] + obj2 + data[end2:start1] + obj1 + data[end1:]

        data = update_references(data, id1, id2)

    write_file(output_file_path, data)

    print("Objects and references have been successfully swapped.")

def replace_galactic_object_section(input_file, replacement_file):
    start_marker = 'galactic_object='
    start_found = False
    bracket_depth = 0
    output_lines = []

    with open(replacement_file, 'r') as rep_file:
        replacement_content = rep_file.readlines()

    with open(input_file, 'r') as infile:
        for line in infile:
            if not start_found:
                if line.strip() == start_marker:
                    start_found = True
                    bracket_depth += line.count('{') - line.count('}')
                    output_lines.append(line)
                    output_lines.extend(replacement_content[1:])
                else:
                    output_lines.append(line)
            else:
                bracket_depth += line.count('{') - line.count('}')
                if bracket_depth == 0:
                    start_found = False
        if not start_found:
            output_lines.append(line)

    temp_output_file = input_file + '.tmp'
    with open(temp_output_file, 'w') as outfile:
        outfile.writelines(output_lines)

    os.replace(temp_output_file, input_file)

def cleanup_files(*file_paths):
    for file_path in file_paths:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted intermediate file: {file_path}")

def create_new_archive(original_file, gamestate_file, meta_file):
    base_name = os.path.splitext(original_file)[0]
    new_archive_name = f"{base_name}.A.sav"
    
    with zipfile.ZipFile(new_archive_name, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(gamestate_file, 'gamestate')
        zipf.write(meta_file, 'meta')

    print(f"Created new archive: {new_archive_name}")

    # Cleanup the extracted gamestate and meta files after creating the archive
    cleanup_files(gamestate_file, meta_file)
if __name__ == "__main__":
    # Find the .sav file in the current directory
    sav_file = []
    for file in os.listdir('.'):
        if file.endswith('.sav'):
            sav_file.append(file)
    i = None
    if len(sav_file) > 1:
        i = int(input(f"bitte zahl eingeben: {enumerate(sav_file)}"))
    if not sav_file:
        print("bitte Pfad angeben")
        print("Wird noch impementiert")
        exit()
    if i == None:
        i = 0

    # Execution steps
    extracted_file_path = 'extracted_galactic_object.txt'
    updated_file_path = 'updated_galactic_object.txt'

    # Step 1: Extract the .sav file
    original_sav_file, gamestate_file, meta_file = extract_sav_file(sav_file[i])
    if not gamestate_file or not meta_file:
        exit()

    # Step 2: Run extraction
    extract_galactic_object_section(gamestate_file, extracted_file_path)

    # Step 3: Process the extracted data
    main_process(extracted_file_path, updated_file_path)

    # Step 4: Replace the section in the original file
    replace_galactic_object_section(gamestate_file, updated_file_path)

    # Step 5: Cleanup intermediate files
    cleanup_files(extracted_file_path, updated_file_path)

    # Step 6: Create a new archive and clean up extracted files
    create_new_archive(original_sav_file, gamestate_file, meta_file)

    # Step 7: Cleanup the original .sav file
    cleanup_files(original_sav_file)
