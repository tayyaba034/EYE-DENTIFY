import os
import re

def fix_deprecated_apis(directory):
    """Fix deprecated Flutter APIs in all Dart files."""
    fixed_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.dart'):
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    
                    # Fix withOpacity -> withValues(alpha:)
                    content = re.sub(r'\.withOpacity\(([0-9.]+)\)', r'.withValues(alpha: \1)', content)
                    
                    # Fix activeColor -> activeTrackColor
                    content = re.sub(r'\bactiveColor:', 'activeTrackColor:', content)
                    
                    if content != original_content:
                        with open(filepath, 'w', encoding='utf-8', newline='') as f:
                            f.write(content)
                        fixed_files.append(filepath)
                        print(f"Fixed: {filepath}")
                
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
    
    return fixed_files

if __name__ == "__main__":
    lib_dir = "d:/frontend test/eye_dentify/lib"
    fixed = fix_deprecated_apis(lib_dir)
    print(f"\nTotal files fixed: {len(fixed)}")
