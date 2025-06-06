import json
import os

def format_crs(txt_path, output_json_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split entries by single blank lines (blocks are separated by one blank line)
    blocks = content.strip().split('\n\n')

    result = []
    for block in blocks:
        # Split each block into lines
        lines = block.splitlines()
        if len(lines) != 2:  # Each block must have exactly 2 lines
            print(f"Skipping invalid block: {block}")
            continue
        try:
            epsg_code, crs_name = lines[0].split('\t')  # Extract EPSG code and CRS name
            epsg_code = int(epsg_code.strip())  # Convert EPSG code to integer
            crs_name = crs_name.strip()  # Strip whitespace from CRS name
            prj_crs = lines[1].strip()  # Extract projection CRS
            result.append({
                "epsg": epsg_code,
                "crs_name": crs_name,
                "prj_crs": prj_crs
            })
        except ValueError as e:
            print(f"Error processing block: {block}, Error: {e}")
            continue

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    '''with open(output_json_path, 'w', encoding='utf-8') as f:
        formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
        # Remove backslashes from escaped double quotes in prj_crs
        formatted_result = formatted_result.replace('\\"', '"')
        f.write(formatted_result)'''
# Paths
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
crsRefTxt_path = os.path.join(parent_dir, "data", "reference", "crs_ref.txt")
formatedCrsJson_path = os.path.join(parent_dir, "data", "reference", "crs_ref.json")

# Run the function
format_crs(crsRefTxt_path, formatedCrsJson_path)