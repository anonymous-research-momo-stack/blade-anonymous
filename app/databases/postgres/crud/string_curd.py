from typing import List

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert

from ..entities import StringLiteralFeatureEntity, association_project_string
from ..postgres import session_generator


def list_strings_by_project_id(project_id: int) -> List[StringLiteralFeatureEntity]:
    """
    Get all related strings by project ID
    """
    with session_generator() as session:
        stmt = select(StringLiteralFeatureEntity).join(
            association_project_string, StringLiteralFeatureEntity.id == association_project_string.c.string_id
        ).where(
            association_project_string.c.project_id == project_id
        )

        return session.execute(stmt).scalars().all()


def add_multiple_string_literals_on_conflict_do_nothing(
        strings: List[str],
) -> List[StringLiteralFeatureEntity]:
    """
    Bulk insert strings, handle duplicates based on unique constraint on content
    """
    if not strings:
        return []

    with session_generator() as session:
        # Insert all strings first, ignore conflicts
        stmt = insert(StringLiteralFeatureEntity).values([
            {"content": s}
            for s in strings
        ])
        stmt = stmt.on_conflict_do_nothing(index_elements=['content'])
        session.execute(stmt)

        # Query all string objects, including existing ones
        all_literals = session.query(StringLiteralFeatureEntity).filter(
            StringLiteralFeatureEntity.content.in_(strings)
        ).all()

        return all_literals


def delete_orphaned_strings() -> int:
    """
    Currently unused.
    Delete strings that have no associations.
    Return the number of deleted strings.
    """
    with session_generator() as session:
        orphaned_strings = session.query(StringLiteralFeatureEntity).filter(
            and_(
                ~StringLiteralFeatureEntity.functions.any(),
                ~StringLiteralFeatureEntity.files.any(),
                ~StringLiteralFeatureEntity.libraries.any()
            )
        ).all()

        count = len(orphaned_strings)
        for string in orphaned_strings:
            session.delete(string)

        return count
