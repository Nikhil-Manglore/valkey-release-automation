import sys
import logging
import re
from typing import Dict, Tuple, Optional

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

def get_newest_version_key(aliases: Dict[str, str]) -> Optional[str]:
    """Get the newest (highest) version key from aliases"""
    if not aliases:
        return None
    
    # Sort by version and return the highest
    sorted_keys = sorted(aliases.keys(), key=parse_version)
    return sorted_keys[-1]

def update_aliases_dict(version: str, aliases: Dict[str, str]) -> Dict[str, str]:
    """Update the aliases dictionary with the new version using simplified logic"""
    try:
        new_major, new_minor = parse_version(version)
        new_key = f"{new_major}.{new_minor}"
        
        # Skip if this exact major.minor already exists in aliases
        if new_key in aliases:
            print(f"Version {new_key} already exists in aliases - no update needed")
            return aliases
        
        # Get current newest version
        current_newest = get_newest_version_key(aliases)
        
        if not current_newest:
            # No existing aliases - add the first one
            print(f"Adding first version {new_key}")
            aliases[new_key] = f"{new_major} latest"
            return aliases
        
        curr_major, curr_minor = parse_version(current_newest)
        
        if new_major == curr_major and new_minor > curr_minor:
            # Same major, newer minor - REPLACE IN-PLACE
            print(f"Updating from {current_newest} to {new_key} (same major, newer minor)")
            
            # Get the old value and transfer it to new key
            old_value = aliases[current_newest]
            del aliases[current_newest]
            aliases[new_key] = old_value
            
        elif new_major > curr_major:
            # New major version - ADD NEW, UPDATE LATEST
            print(f"Adding new major version {new_major} (upgrading from major {curr_major})")
            
            # Remove 'latest' from current newest
            if 'latest' in aliases[current_newest]:
                aliases[current_newest] = aliases[current_newest].replace(' latest', '').strip()
            
            # Add new major version with 'latest'
            aliases[new_key] = f"{new_major} latest"
            
        else:
            # Lower or equal version - no changes needed
            print(f"Version {new_key} is not newer than current newest {current_newest} - no changes made")
        
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
        
        # Make a copy to detect changes
        original_aliases = aliases.copy()
        
        # Update aliases using simplified logic
        updated_aliases = update_aliases_dict(version, aliases)
        
        # Check if aliases actually changed
        if original_aliases == updated_aliases:
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
