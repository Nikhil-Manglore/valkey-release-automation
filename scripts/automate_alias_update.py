import sys
import logging
import re
from typing import Dict, Tuple

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def parse_current_aliases(script_path: str) -> Dict[str, str]:
    """Parse the current aliases from generate-stackbrew-library.sh"""
    try:
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Find the aliases declaration block
        aliases_pattern = r'declare -A aliases=\(\s*(.*?)\s*\)'
        match = re.search(aliases_pattern, content, re.DOTALL)
        
        if not match:
            raise ValueError("Could not find aliases declaration in script")
        
        aliases_content = match.group(1)
        aliases = {}
        
        # Parse each alias line: [8.1]='8 latest'
        line_pattern = r'\[([^\]]+)\]=\'([^\']*)\''
        for line_match in re.finditer(line_pattern, aliases_content):
            key = line_match.group(1)
            value = line_match.group(2)
            aliases[key] = value
        
        return aliases
    
    except FileNotFoundError:
        logging.error(f"Script file not found: {script_path}")
        raise
    except Exception as e:
        logging.error(f"Error parsing aliases from {script_path}: {e}")
        raise

def parse_version(version: str) -> Tuple[int, int]:
    """Parse version string into (major, minor) tuple"""
    try:
        parts = version.split('.')
        if len(parts) < 2:
            raise ValueError(f"Invalid version format: {version}")
        return int(parts[0]), int(parts[1])
    except ValueError as e:
        logging.error(f"Error parsing version {version}: {e}")
        raise

def update_aliases_dict(version: str, aliases: Dict[str, str]) -> Dict[str, str]:
    """Update the aliases dictionary with the new version"""
    try:
        new_major, new_minor = parse_version(version)
        new_key = f"{new_major}.{new_minor}"
        
        # Skip if this exact major.minor already exists in aliases
        if new_key in aliases:
            print(f"Version {new_key} already exists in aliases - no update needed")
            return aliases
        
        # Find current highest major version
        existing_majors = [parse_version(k)[0] for k in aliases.keys()]
        current_highest_major = max(existing_majors) if existing_majors else 0
        
        if new_major > current_highest_major:
            # NEW MAJOR VERSION (e.g., 9.0 when current highest is 8.x)
            print(f"Adding new major version {new_major}")
            
            # Remove "latest" from previous highest major
            for key in list(aliases.keys()):
                if 'latest' in aliases[key]:
                    aliases[key] = aliases[key].replace(' latest', '').strip()
            
            # Add new major version with "latest"
            aliases[new_key] = f"{new_major} latest"
            
        elif new_major == current_highest_major:
            # NEW MINOR within current highest major (e.g., 8.2 when we have 8.1)
            print(f"Updating to newer minor version {new_key} within major {new_major}")
            
            # Remove old minor versions for this major (keep other majors)
            keys_to_remove = [k for k in aliases if parse_version(k)[0] == new_major]
            for key in keys_to_remove:
                del aliases[key]
            
            # Add new minor version with "latest" (if this is the highest major)
            aliases[new_key] = f"{new_major} latest"
        
        else:
            # Lower major version - no changes needed
            print(f"Version {new_key} is older than current highest major {current_highest_major} - no changes made")
        
        return aliases
    
    except Exception as e:
        logging.error(f"Error updating aliases dictionary: {e}")
        raise

def update_container_aliases(script_path: str, version: str) -> None:
    """Main function to update container aliases"""
    try:
        # Parse current aliases
        aliases = parse_current_aliases(script_path)
        print(f"Current aliases: {aliases}")
        
        # Update aliases
        updated_aliases = update_aliases_dict(version, aliases)
        
        # Check if aliases actually changed
        if aliases == updated_aliases:
            print(f"No alias changes needed for version {version}")
            return
        
        print(f"Updating aliases for new version {version}")
        
        # Write back to file
        with open(script_path, 'r') as f:
            content = f.read()

        # Build new aliases declaration
        alias_lines = [
            f"\t[{key}]='{updated_aliases[key]}'"
            for key in sorted(updated_aliases.keys(), key=parse_version)
        ]
        new_aliases_block = "declare -A aliases=(\n" + "\n".join(alias_lines) + "\n)"

        # Replace the old aliases declaration
        aliases_pattern = r'declare -A aliases=\(\s*.*?\s*\)'
        new_content = re.sub(aliases_pattern, new_aliases_block, content, flags=re.DOTALL)

        with open(script_path, 'w') as f:
            f.write(new_content)
        
        print(f"Successfully updated aliases in {script_path}")
        print(f"New aliases: {updated_aliases}")
    
    except Exception as e:
        logging.error(f"Failed to update container aliases: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        logging.error("Invalid number of arguments.")
        logging.error("Usage: python update_container_aliases.py <script_path> <version>")
        sys.exit(1)
    
    try:
        update_container_aliases(sys.argv[1], sys.argv[2])
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        sys.exit(1)
