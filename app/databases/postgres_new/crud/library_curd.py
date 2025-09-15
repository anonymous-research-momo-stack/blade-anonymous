from typing import List
from typing import Optional

from sqlalchemy import func

from ..entities import StringFeature, StringToLibrary, Library
from ..postgres import session_generator


def list_libraries_by_strings(strings: List[str], min_match_num: int = 5):
    """
    Query libraries that have at least the specified number of intersections
    with the given list of strings.

    Args:
        strings: The list of strings to query
        min_match_num: Minimum number of matching strings, default 5

    Returns:
        A list of matched libraries. Each library object contains a list of
        matched strings.
    """
    with session_generator() as session:
        # 1. First, query the matched string IDs and values
        string_features = (
            session.query(StringFeature.id, StringFeature.string_value)
            .filter(StringFeature.string_value.in_(strings))
            .all()
        )

        if not string_features:
            return []

        # 2. Query string-library relations and find library IDs that satisfy the condition
        library_matches = (
            session.query(
                StringToLibrary.library_id,
                func.array_agg(StringFeature.string_value).label('matched_strings')
            )
            .join(
                StringFeature,
                StringFeature.id == StringToLibrary.string_id
            )
            .filter(StringToLibrary.string_id.in_([sf_id for sf_id, _ in string_features]))
            .group_by(StringToLibrary.library_id)
            .having(func.count(StringToLibrary.string_id) >= min_match_num)
            .all()
        )

        if not library_matches:
            return []

        # 3. Query matched library information
        matched_libraries = (
            session.query(Library)
            .filter(Library.id.in_([lib_id for lib_id, _ in library_matches]))
            .all()
        )

        # 4. Build results and attach matched string info
        # Create a mapping from library_id to matched_strings
        library_strings_map = {
            lib_id: sorted(set(matched_strings), key=lambda x: len(x), reverse=True)
            for lib_id, matched_strings in library_matches
        }

        # Add matched_strings attribute to each library
        for library in matched_libraries:
            library.matched_strings = library_strings_map[library.id]

        # Sort by the number of matched strings
        matched_libraries = sorted(
            matched_libraries, 
            key=lambda x: len(library_strings_map[x.id]), 
            reverse=True
        )

        return matched_libraries





def get_library_string_count(library_name: str) -> Optional[int]:
    """
    Query the number of strings associated with the specified library name

    Args:
        library_name: The name of the library

    Returns:
        The number of strings related to the library, or None if the library
        does not exist
    """
    with session_generator() as session:
        # Query the number of strings for the specified library name
        result = session.query(func.count(StringToLibrary.string_id.distinct())) \
            .join(Library, StringToLibrary.library_id == Library.id) \
            .filter(Library.name == library_name) \
            .scalar()

        # If the result is 0, confirm whether the library exists
        if result == 0:
            library_exists = session.query(Library) \
                .filter(Library.name == library_name) \
                .first()
            if not library_exists:
                return None

        return result