import hashlib
from typing import List, Dict, Any
import os
import subprocess
import traceback
from pathlib import Path

import lief
from loguru import logger

from ....interface import TargetBinary
from ..agent_analysis.string_filter import StringFilter


def calculate_file_sha256(file_path):
    """
    Calculate SHA256 hash value of the specified file

    Args:
        file_path (str): File path

    Returns:
        str: SHA256 hash value of the file (hexadecimal string)

    Raises:
        FileNotFoundError: If file does not exist
        PermissionError: If no permission to read the file
        OSError: Other file operation errors
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exist: {file_path}")

    # Check if it is a file (not a directory)
    if not os.path.isfile(file_path):
        raise ValueError(f"Path is not a file: {file_path}")

    # Create SHA256 hash object
    sha256_hash = hashlib.sha256()

    try:
        # Open file in binary mode
        with open(file_path, 'rb') as file:
            # Read file content in chunks to avoid excessive memory usage for large files
            for chunk in iter(lambda: file.read(4096), b""):
                sha256_hash.update(chunk)
    except PermissionError:
        raise PermissionError(f"No permission to read file: {file_path}")
    except OSError as e:
        raise OSError(f"Error occurred while reading file: {e}")

    # Return hash value in hexadecimal format
    return sha256_hash.hexdigest()

class FilePreprocessor:

    def __init__(self,
                 # StringFilter related parameters
                 max_copyright: int = 15,  # Maximum number of copyright information to display
                 max_paths: int = 20,  # Maximum number of path URLs to display
                 max_function_prefixes: int = 15,  # Maximum number of function prefixes to display
                 max_logs: int = 10,  # Maximum number of log messages to display
                 max_versions: int = 8,  # Maximum number of version information to display
                 max_string_length: int = 200,  # Maximum length of a single string
                 ):
        # StringFilter configuration
        self.string_filter = StringFilter(
            max_copyright=max_copyright,
            max_paths=max_paths,
            max_function_prefixes=max_function_prefixes,
            max_logs=max_logs,
            max_versions=max_versions,
            max_string_length=max_string_length
        )
        pass


    def basic_analyze(self, file_path, root_path=None,

                      ) -> TargetBinary:
        """
        Perform basic analysis on binary files, extract string information and dynamic linking information

        Args:
            file_path: Binary file path
            root_path: Root directory path, used to calculate relative path. If None, use file_path as root directory

        Returns:
            TargetBinary: Object containing analysis results
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File does not exist: {file_path}")

        # Get basic file information
        file_path_obj = Path(file_path)
        file_size_kb = file_path_obj.stat().st_size // 1024  # Convert to KB

        # Calculate relative path
        if root_path is None:
            root_path = file_path

        root_path_obj = Path(root_path)
        file_path_absolute = file_path_obj.absolute()
        root_path_absolute = root_path_obj.absolute()

        # If root directory and file path are the same, use root directory
        if file_path_absolute == root_path_absolute:
            relative_path = root_path_obj.name
        else:
            # Calculate path relative to root directory
            try:
                relative_path = str(file_path_absolute.relative_to(root_path_absolute))
            except ValueError:
                # If file is not under root directory, use file name
                relative_path = file_path_obj.name

        # Extract dynamic libraries, imports, and export symbol table
        dynamic_linked_libraries, imported_symbols, exported_symbols = self._lief_parse(file_path)

        # Extract strings using strings command
        strings_list = self._extract_strings(file_path)

        # Filter and categorize strings
        filtered_strings = self.string_filter.filter_strings(strings_list)

        # Create TargetBinary object
        target_binary = TargetBinary(
            binary_name=file_path_obj.name,
            hash_sha256= calculate_file_sha256(file_path),
            relative_path=relative_path,
            absolute_path=str(file_path_absolute),
            file_size_kb=file_size_kb,
            strings=list(set(strings_list)),
            classified_strings=filtered_strings,
            dynamic_libraries=dynamic_linked_libraries,
            imported_symbols=list(set(imported_symbols)),
            exported_symbols=list(set(exported_symbols)),
            imported_symbol_analysis=self._analyze_imported_symbols(imported_symbols),
            exported_symbol_analysis=self._analyze_exported_symbols(exported_symbols),
        )

        return target_binary

    def _extract_strings(self, file_path: str) -> List[str]:
        """
        Extract strings from binary file using strings command

        Args:
            file_path: Binary file path

        Returns:
            List[str]: List of extracted strings
        """
        try:
            # Use strings command, set minimum length to 5 for strings
            result = subprocess.run(
                ['strings', '-n', '5', file_path],
                capture_output=True,
                text=True,
                timeout=30  # Set timeout
            )

            if result.returncode == 0:
                # Split output and filter empty strings
                # Sort after strings extraction
                strings = sorted([line.strip() for line in result.stdout.split('\n') if line.strip()])
                return strings
            else:
                logger.debug(f"strings command execution failed: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            logger.debug(f"strings command execution timeout: {file_path}")
            return []
        except FileNotFoundError:
            logger.debug("strings command not found, please ensure the system has strings tool installed")
            return []
        except Exception as e:
            logger.error(f"Error occurred while extracting strings: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []


    def _lief_parse(self, file_path):
        """
        Get dynamic libraries of binary file

        Args:
            file_path (str): Binary file path

        Returns:
            list: Dynamic library name list
        """
        try:
            binary = lief.parse(file_path)
            if binary is None:
                return [],[],[]
            # In _lief_parse method
            dynamic_linked_libraries = sorted(list(binary.libraries))
            imported_symbols = sorted([symbol.name for symbol in binary.imported_symbols if symbol.name])
            exported_symbols = sorted([symbol.name for symbol in binary.exported_symbols if symbol.name])
            return dynamic_linked_libraries, imported_symbols, exported_symbols
        except:
            return [],[],[]

    # TODO tpl_analyzer also has an implementation, make them the same.
    def _analyze_exported_symbols(self, exported_symbols: list) -> Dict[str, Any]:
        """Analyze exported symbols by function prefix classification"""
        if not exported_symbols:
            return {}

        prefix_categories = {}

        for symbol in exported_symbols:
            # Extract prefix (to first underscore)
            if '_' in symbol:
                prefix = symbol.split('_')[0]
            else:
                # If no underscore, take first few characters as prefix
                import re
                match = re.match(r'^[a-zA-Z]+', symbol)
                prefix = match.group()[:4] if match else 'other'

            # Only count meaningful prefixes (length >= 2)
            if len(prefix) >= 2:
                if prefix not in prefix_categories:
                    prefix_categories[prefix] = []
                prefix_categories[prefix].append(symbol)

        # Organize results: give a few examples for each prefix category
        result = {
            'total_exported': len(exported_symbols),
            'prefix_categories': {}
        }

        # In _analyze_exported_symbols and _analyze_imported_symbols
        # Sort and iterate through prefix_categories keys
        for prefix in sorted(prefix_categories.keys()):
            symbols = prefix_categories[prefix]
            if len(symbols) >= 1:
                result['prefix_categories'][prefix] = {
                    'count': len(symbols),
                    'examples': sorted(symbols)[:3]  # Sort examples as well
                }

        return result

    def _analyze_imported_symbols(self, imported_symbols: list) -> Dict[str, Any]:
        """Analyze prefix patterns of imported symbols"""
        if not imported_symbols:
            return {}

        prefix_categories = {}

        for symbol in imported_symbols:
            # Extract prefix (to first underscore)
            if '_' in symbol:
                prefix = symbol.split('_')[0]
            else:
                # If no underscore, take first few characters as prefix
                import re
                match = re.match(r'^[a-zA-Z]+', symbol)
                prefix = match.group()[:4] if match else 'other'

            # Only count meaningful prefixes (length >= 2)
            if len(prefix) >= 2:
                if prefix not in prefix_categories:
                    prefix_categories[prefix] = []
                prefix_categories[prefix].append(symbol)

        # Only keep prefixes with multiple symbols
        significant_prefixes = {k: v for k, v in prefix_categories.items() if len(v) >= 2}

        result = {
            'total_imported': len(imported_symbols),
            'significant_prefixes': {}
        }

        # In _analyze_exported_symbols and _analyze_imported_symbols
        # Sort and iterate through prefix_categories keys
        for prefix in sorted(prefix_categories.keys()):
            symbols = prefix_categories[prefix]
            if len(symbols) >= 1:
                result['significant_prefixes'][prefix] = {
                    'count': len(symbols),
                    'examples': sorted(symbols)[:3]  # Sort examples as well
                }

        return result