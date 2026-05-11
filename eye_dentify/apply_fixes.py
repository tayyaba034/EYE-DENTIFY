import os
import re

def fix_content(content):
    # Regex for .withOpacity(0.X) -> .withValues(alpha: 0.X)
    # Handles integers (0, 1) and floats (0.5, .5)
    content = re.sub(r'\.withOpacity\(([0-9]*\.?[0-9]+)\)', r'.withValues(alpha: \1)', content)
    # Regex for activeColor: -> activeTrackColor:
    content = re.sub(r'activeColor:', 'activeTrackColor:', content)
    return content

root_dir = 'd:/frontend test/eye_dentify/lib'
print(f"Scanning {root_dir}...")

count = 0
for dirpath, _, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.endswith('.dart'):
            fullpath = os.path.join(dirpath, filename)
            try:
                with open(fullpath, 'r', encoding='utf-8') as f:
                    original = f.read()
                
                fixed = fix_content(original)
                
                if original != fixed:
                    with open(fullpath, 'w', encoding='utf-8') as f:
                        f.write(fixed)
                    print(f"Fixed {filename}")
                    count += 1
            except Exception as e:
                print(f"Failed to process {filename}: {e}")

print(f"Done. Fixed {count} files.")
