import re
from typing import List

from loguru import logger

from ....databases.postgres.entities import ProjectFeatureEntity
from ....interface import TargetBinary, Library
from ....databases.postgres_new.crud import library_curd
from ....databases.postgres.crud import project_curd
from ....config import settings


def _is_cpp_function_name(string: str) -> bool:
    """
    Check if string conforms to C/C++ function name rules

    Args:
        string: String to check

    Returns:
        bool: Whether it is a C/C++ function name
    """
    import re

    # Remove leading and trailing whitespace
    s = string.strip()

    # Empty string or too short string is not a function name
    if len(s) < 2:
        return False

    # C/C++ function name rules:
    # 1. Can only contain letters, numbers, underscores
    # 2. Cannot start with a number
    # 3. Cannot be a C++ keyword
    # 4. Usually contains letters (pure numbers are not function names)

    # Check if it only contains legal characters
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', s):
        return False

    # Check if it contains letters (pure numbers are not function names)
    if not re.search(r'[a-zA-Z]', s):
        return False

    # Check if it is a C++ keyword
    cpp_keywords = {
        'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
        'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
        'int', 'long', 'register', 'return', 'short', 'signed', 'sizeof', 'static',
        'struct', 'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile', 'while',
        'asm', 'bool', 'catch', 'class', 'const_cast', 'delete', 'dynamic_cast',
        'explicit', 'export', 'false', 'friend', 'inline', 'mutable', 'namespace',
        'new', 'operator', 'private', 'protected', 'public', 'reinterpret_cast',
        'static_cast', 'template', 'this', 'throw', 'true', 'try', 'typeid',
        'typename', 'using', 'virtual', 'wchar_t'
    }

    if s.lower() in cpp_keywords:
        return False

    # Check for common function name patterns
    # 1. Contains common prefixes/suffixes
    common_prefixes = ['get', 'set', 'is', 'has', 'can', 'should', 'will', 'do', 'make', 'create', 'init',
                       'destroy', 'free', 'alloc', 'dealloc']
    common_suffixes = ['_t', '_ptr', '_ref', '_impl', '_base', '_derived']

    s_lower = s.lower()
    for prefix in common_prefixes:
        if s_lower.startswith(prefix) and len(s) > len(prefix):
            return True

    for suffix in common_suffixes:
        if s_lower.endswith(suffix):
            return True

    # 2. Check if it is camelCase or snake_case naming
    # CamelCase: getValue, setValue, isEnabled
    if re.match(r'^[a-z][a-zA-Z0-9]*$', s) or re.match(r'^[A-Z][a-zA-Z0-9]*$', s):
        return True

    # Snake_case: get_value, set_value, is_enabled
    if re.match(r'^[a-z][a-z0-9_]*$', s) and '_' in s:
        return True

    # 3. Check if it contains common function name patterns
    function_patterns = [
        r'^[a-zA-Z_][a-zA-Z0-9_]*$',  # Basic function name pattern
        r'.*[A-Z].*',  # Contains uppercase letters (possibly camelCase)
        r'.*_.*',  # Contains underscores
    ]

    for pattern in function_patterns:
        if re.match(pattern, s):
            return True

    return False


class FeatureMatchingDetector:
    """
    Feature matching detector
    Used to detect the matching degree between binary files and known libraries
    """

    def __init__(self,
                 top_n: int = 5,
                 feature_min_length=5,
                 feature_max_length=500,
                 min_match_feature_num: int = 5,
                 containment_threshold: float = 0.9,  # Containment threshold
                 size_ratio_threshold: float = 0.3):  # Size ratio threshold
        """
        Initialize feature matching detector

        Args:
            top_n: Return top N candidate libraries
            min_match_feature_num: Minimum number of matching strings
            containment_threshold: Containment threshold for judging subset relationships
            size_ratio_threshold: Size ratio threshold for judging common feature matching
        """
        self.top_n = top_n
        self.min_match_num = min_match_feature_num
        self.feature_min_length = feature_min_length
        self.feature_max_length = feature_max_length
        self.min_effective_string_length = 10
        self.containment_threshold = containment_threshold
        self.size_ratio_threshold = size_ratio_threshold

        self.method_name = "Feature Matching"

        self.use_new_data_base = settings.use_new_database

    def detect(self, target_binary: TargetBinary) -> List[Library]:
        """
        Run feature matching detection

        Args:
            target_binary: Target binary file object

        Returns:
            List[Library]: List of matched candidate libraries (Library interface type)
        """
        if not target_binary.strings:
            logger.warning(f"No strings provided for binary: {target_binary.binary_name}")
            return []

        logger.debug(
            f"Starting feature matching detection for binary: {target_binary.binary_name} with {len(target_binary.strings)} strings")

        # Filter features
        strings = self.filter_strings_to_match(target_binary)
        # Call matching logic
        return self.match_candidate_libraries(target_binary.binary_name, strings)

    def filter_and_rank_candidates(self, candidate_project_entities: List[ProjectFeatureEntity]) -> List[
        ProjectFeatureEntity]:
        """
        Sort and filter candidate libraries, removing garbage results from common feature matching

        Core strategy: Remove libraries that meet both of the following conditions:
        1. More than 90% of this library's features are in a previous library (high containment)
        2. The total number of features of this library does not exceed 30% of the previous library (low proportion)

        Such libraries are most likely garbage results that were coincidentally matched through some common features.

        Args:
            candidate_project_entities: Original candidate library list

        Returns:
            Filtered candidate library list
        """
        if not candidate_project_entities:
            return []

        def cal_effective_string_num(project_entity: ProjectFeatureEntity) -> int:
            """Calculate the number of effective strings"""
            effective_num = 0
            for s in project_entity.matched_strings:
                if " " not in s and len(s) < self.min_effective_string_length:
                    continue
                effective_num += 1
            return effective_num

        # 1. Sort first by string count, then by effective string count
        sorted_candidates = sorted(candidate_project_entities,
                                   key=lambda x: len(x.matched_strings),
                                   reverse=True)

        sorted_candidates = sorted(sorted_candidates,
                                   key=cal_effective_string_num,
                                   reverse=True)

        # 2. Take the first top_n as initial results
        initial_candidates = sorted_candidates[:self.top_n]

        # 3. Apply filtering strategy: remove garbage matches
        filtered_candidates = []

        for current_candidate in initial_candidates:
            current_features = set(current_candidate.matched_strings)
            is_garbage = False

            # Check if current candidate library is a garbage match for libraries that have passed filtering
            for previous_candidate in filtered_candidates:
                previous_features = set(previous_candidate.matched_strings)

                # Calculate containment relationship
                intersection = current_features & previous_features
                containment_ratio = len(intersection) / len(current_features) if current_features else 0
                size_ratio = len(current_features) / len(previous_features) if previous_features else 0

                # Determine if it is a garbage match
                if (containment_ratio >= self.containment_threshold and
                        size_ratio <= self.size_ratio_threshold):
                    logger.debug(f"Filtering out garbage match: {current_candidate.name} "
                                 f"(containment: {containment_ratio:.3f}, size_ratio: {size_ratio:.3f}) "
                                 f"is subset of {previous_candidate.name}")
                    is_garbage = True
                    break

            if not is_garbage:
                filtered_candidates.append(current_candidate)

        # 4. Record filtering effect
        removed_count = len(initial_candidates) - len(filtered_candidates)
        if removed_count > 0:
            logger.debug(f"Filtered out {removed_count} garbage matches from {len(initial_candidates)} initial candidates")

        return filtered_candidates

    def filter_strings_to_match(self, target_binary: TargetBinary) -> List[str]:
        filter_out_set = {".note.gnu.build-id", ".gnu.version_r", ".eh_frame_hdr", ".data.rel.ro", ".gnu.version",
                          ".fini_array", ".init_array", ".eh_frame", ".rela.plt", ".shstrtab", ".gnu.hash", ".rela.dyn",
                          ".dynamic", ".comment", ".got.plt", ".plt.got", ".rodata", ".dynsym", ".dynstr"}
        strings_to_match = set()
        for s in target_binary.strings:
            if s in filter_out_set:
                continue

            if not (self.feature_min_length < len(s) < self.feature_max_length):
                continue

            # Exclude strings that conform to function name rules, do not match function names
            if _is_cpp_function_name(s):
                continue

            strings_to_match.add(s.strip())

        return sorted(strings_to_match)

    def match_candidate_libraries(self, file_name: str, strings: List[str]) -> List[Library]:
        """
        Match candidate libraries
        Must match at least min_match_num strings
        Strings must: have length greater than min_effective_string_length or contain spaces, or be libraries with similar names

        Args:
            file_name: File name
            strings: String list

        Returns:
            List[Library]: List of matched candidate libraries (Library interface type)
        """
        # 1. Database matching - query database by strings first, must match at least min_match_num strings
        if self.use_new_data_base:
            candidate_project_entities = library_curd.list_libraries_by_strings(strings, min_match_num=self.min_match_num)
        else:
            candidate_project_entities = project_curd.list_projects_by_strings(strings, min_match_num=self.min_match_num)
        if not candidate_project_entities:
            logger.info(f"No candidate libraries found for file: {file_name}")
            return []

        # 2. Apply new sorting and filtering strategy
        filter_candidate_project_entities = self.filter_and_rank_candidates(candidate_project_entities)

        # 3. Libraries with similar names are also considered as candidates (preserve original logic)
        file_name_for_check = self._prepare_filename_for_check(file_name)

        for project_entity in candidate_project_entities:
            if project_entity not in filter_candidate_project_entities:
                if self._is_similar_name(file_name_for_check, project_entity.name):
                    if project_entity not in filter_candidate_project_entities:
                        filter_candidate_project_entities.append(project_entity)
                        logger.debug(f"Added similar name library: {project_entity.name} for file: {file_name}")

        # 4. Convert to Library interface type
        candidate_libraries = self._convert_to_library_interface(filter_candidate_project_entities)

        logger.debug(f"Found {len(candidate_libraries)} candidate libraries for file: {file_name}")

        return candidate_libraries

    def _prepare_filename_for_check(self, file_name: str) -> str:
        """
        Prepare filename for checking

        Args:
            file_name: Original filename

        Returns:
            Processed filename
        """
        file_name_for_check = file_name.lower().split(".")[0]
        if "lib" in file_name_for_check and len(file_name_for_check) >= 7:
            file_name_for_check = file_name_for_check[3:]
        return file_name_for_check

    def _is_similar_name(self, file_name: str, library_name: str) -> bool:
        """
        Check if filename and library name are similar

        The matching part must be an independent word, separated by special characters before and after

        Args:
            file_name: Processed filename
            library_name: Library name

        Returns:
            Whether they are similar
        """
        # Define word boundary separator pattern
        word_boundary = r'[\s_\-/\.\|\\\+\*\(\)\[\]\{\}\,\;\:\!\?\@\#\$\%\^\&\=\~\`]'

        # Escape special characters to avoid regex conflicts
        escaped_file_name = re.escape(file_name.lower())
        escaped_library_name = re.escape(library_name.lower())

        # Build regex pattern: (start|separator) + target word + (separator|end)
        file_pattern = f'(^|{word_boundary}){escaped_file_name}({word_boundary}|$)'
        library_pattern = f'(^|{word_boundary}){escaped_library_name}({word_boundary}|$)'

        # Bidirectional check
        return (re.search(file_pattern, library_name.lower()) is not None or
                re.search(library_pattern, file_name.lower()) is not None)

    def _convert_to_library_interface(self, project_entities: List[ProjectFeatureEntity]) -> List[Library]:
        """
        Convert database entities to Library interface type

        Args:
            project_entities: Database project entity list

        Returns:
            Library interface type list
        """
        libraries = []
        for project_entity in project_entities:
            # Get library description information
            description = ""
            if hasattr(project_entity, 'library') and project_entity.library:
                description = project_entity.library.description or ""

            # Create Library object
            library = Library(
                name=project_entity.name,
                id=project_entity.id,
                description=description,
                matched_strings=project_entity.matched_strings,
                identify_methods=[self.method_name],
                reasoning=f"Based on feature matching method, it matched {len(project_entity.matched_strings)} strings. ",
            )

            libraries.append(library)

        return libraries


