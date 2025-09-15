from loguru import logger
from sqlalchemy.orm import joinedload

from ..entities import ProjectFeatureEntity, StringLiteralFeatureEntity, association_project_string
from ..postgres import session_generator


def cascade_add_project_feature(
        project_feature: ProjectFeatureEntity,
):
    """
    Cascade add project feature
    1. Validate existence first; skip if exists
    2. Add project
    3. Add files
    4. Add file-string associations
    5. Add functions
    6. Add function-string associations

    :param project_feature:
    :return:
    """
    with session_generator() as session:
        # Check existence first; skip if exists
        result = session.get(ProjectFeatureEntity, project_feature.id)
        if result is not None:
            logger.debug(result)
            logger.info(f"project {project_feature.id}: {project_feature.name} already exists. skip insert.")
            return False

        # Insert project
        logger.info(f"insert project {project_feature.id}: {project_feature.name}")
        session.add(project_feature)
        session.flush()

        # The following parts will be automatically cascaded; manual insert is not needed
        #
        # # Insert files
        # logger.info(f"insert project {project_feature.id}: {project_feature.name} files")
        # for file_feature in project_feature.files:
        #     # Update ids
        #     file_feature.library_id = project_feature.library_id
        #     file_feature.project_id = project_feature.id
        #     session.add(file_feature)
        # session.flush()
        #
        # # File-string associations
        # logger.info(f"insert project {project_feature.id}: {project_feature.name} file-string associations")
        # # Deduplicate
        # file_string_mapping_set = set()
        # for file_feature in project_feature.files:
        #     for string_literal in file_feature.string_literals:
        #         file_string_mapping_set.add((file_feature.id, string_literal.id))
        # # Transform to list of dicts
        # # Transform to list of dicts
        # file_string_mapping = [{
        #     'file_id': file_feature_id,
        #     'string_id': string_literal_id
        # } for file_feature_id, string_literal_id in file_string_mapping_set]
        #
        # session.execute(association_file_string.insert(), file_string_mapping)
        #
        # # Insert functions
        # logger.info(f"insert project {project_feature.id}: {project_feature.name} functions")
        # for file_feature in project_feature.files:
        #     for function_feature in file_feature.functions:
        #         function_feature.file_id = file_feature.id
        #         function_feature.library_id = project_feature.library_id
        #         function_feature.project_id = project_feature.id
        #         session.add(function_feature)
        # session.flush()
        #
        # # Function-string associations
        # logger.info(f"insert project {project_feature.id}: {project_feature.name} function-string associations")
        # # Deduplicate
        # function_string_mapping_set = set()
        # for file_feature in project_feature.files:
        #     for function_feature in file_feature.functions:
        #         for string_literal in function_feature.string_literals:
        #             function_string_mapping_set.add((function_feature.id, string_literal.id))
        # # Transform to list of dicts
        # function_string_mapping = [{
        #     'function_id': function_feature_id,
        #     'string_id': string_literal_id
        # } for function_feature_id, string_literal_id in function_string_mapping_set]
        #
        # session.execute(association_function_string.insert(), function_string_mapping)
        # logger.info(f"cascade insert project {project_feature.id}: {project_feature.name} success.")





from typing import List, Optional
from sqlalchemy import func


def list_projects_by_strings(strings: List[str], min_match_num: int = 5):
    """
    Query projects having at least N intersections with given strings

    Args:
        strings: strings to query

    Returns:
        matched project list, each project contains matched string list
    """
    with session_generator() as session:
        # 1. Query matched string ids first
        string_ids = (
            session.query(StringLiteralFeatureEntity.id, StringLiteralFeatureEntity.content)
            .filter(StringLiteralFeatureEntity.content.in_(strings))
            .all()
        )

        if not string_ids:
            return []

        # 2. Query string-project associations and find qualified project ids
        project_ids = (
            session.query(
                association_project_string.c.project_id,
                func.array_agg(StringLiteralFeatureEntity.content).label('matched_strings')
            )
            .join(
                StringLiteralFeatureEntity,
                StringLiteralFeatureEntity.id == association_project_string.c.string_id
            )
            .filter(association_project_string.c.string_id.in_([sid for sid, _ in string_ids]))
            .group_by(association_project_string.c.project_id)
            .having(func.count(association_project_string.c.string_id) >= min_match_num)
            .all()
        )

        if not project_ids:
            return []

        # 3. Query matched projects
        matched_projects = (
            session.query(ProjectFeatureEntity)
            .filter(ProjectFeatureEntity.id.in_([pid for pid, _ in project_ids]))
            .options(joinedload(ProjectFeatureEntity.library))
            .all()
        )

        # 4. Build result and add matched strings
        # Create project_id to matched_strings mapping
        project_strings_map = {pid: sorted(set(matched_strings), key=lambda x: len(x), reverse=True)
                               for pid, matched_strings in project_ids}

        # Add matched_strings attribute for each project
        for project in matched_projects:
            project.matched_strings = project_strings_map[project.id]

        matched_projects = sorted(matched_projects, key=lambda x: len(project_strings_map[project.id]), reverse=True)

        return matched_projects
