from loguru import logger
from sqlalchemy.orm import joinedload

from ..entities import ProjectFeatureEntity, StringLiteralFeatureEntity, association_project_string
from ..postgres import session_generator


def cascade_add_project_feature(
        project_feature: ProjectFeatureEntity,
):
    """
    级联添加 project feature
    1. 先验证是否存在，存在则不添加
    2. 添加 project
    3. 添加 file
    4. 添加 file-string associations
    5. 添加 function
    6. 添加 function-string associations

    :param project_feature:
    :return:
    """
    with session_generator() as session:
        # 先查询是否存在，存在则不添加
        result = session.get(ProjectFeatureEntity, project_feature.id)
        if result is not None:
            logger.debug(result)
            logger.info(f"project {project_feature.id}: {project_feature.name} already exists. skip insert.")
            return False

        # 添加 project
        logger.info(f"insert project {project_feature.id}: {project_feature.name}")
        session.add(project_feature)
        session.flush()

        # 以下部分会自动级联添加，不需要手动添加
        #
        # # 添加 file
        # logger.info(f"insert project {project_feature.id}: {project_feature.name} files")
        # for file_feature in project_feature.files:
        #     # 更新id
        #     file_feature.library_id = project_feature.library_id
        #     file_feature.project_id = project_feature.id
        #     session.add(file_feature)
        # session.flush()
        #
        # # 文件与字符串的关联关系
        # logger.info(f"insert project {project_feature.id}: {project_feature.name} file-string associations")
        # # 去重
        # file_string_mapping_set = set()
        # for file_feature in project_feature.files:
        #     for string_literal in file_feature.string_literals:
        #         file_string_mapping_set.add((file_feature.id, string_literal.id))
        # # 转换为dict列表
        # file_string_mapping = [{
        #     'file_id': file_feature_id,
        #     'string_id': string_literal_id
        # } for file_feature_id, string_literal_id in file_string_mapping_set]
        #
        # session.execute(association_file_string.insert(), file_string_mapping)
        #
        # # 添加函数
        # logger.info(f"insert project {project_feature.id}: {project_feature.name} functions")
        # for file_feature in project_feature.files:
        #     for function_feature in file_feature.functions:
        #         function_feature.file_id = file_feature.id
        #         function_feature.library_id = project_feature.library_id
        #         function_feature.project_id = project_feature.id
        #         session.add(function_feature)
        # session.flush()
        #
        # # 函数与字符串的关联关系
        # logger.info(f"insert project {project_feature.id}: {project_feature.name} function-string associations")
        # # 去重
        # function_string_mapping_set = set()
        # for file_feature in project_feature.files:
        #     for function_feature in file_feature.functions:
        #         for string_literal in function_feature.string_literals:
        #             function_string_mapping_set.add((function_feature.id, string_literal.id))
        # # 转换为dict列表
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
    查询与给定字符串列表至少有5个交集的库

    Args:
        strings: 要查询的字符串列表

    Returns:
        匹配的库列表，每个库对象包含匹配的字符串列表
    """
    with session_generator() as session:
        # 1. 首先查询匹配的字符串ID
        string_ids = (
            session.query(StringLiteralFeatureEntity.id, StringLiteralFeatureEntity.content)
            .filter(StringLiteralFeatureEntity.content.in_(strings))
            .all()
        )

        if not string_ids:
            return []

        # 2. 查询字符串-库关联关系，并找到满足条件的库ID
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

        # 3. 查询匹配的库信息
        matched_projects = (
            session.query(ProjectFeatureEntity)
            .filter(ProjectFeatureEntity.id.in_([pid for pid, _ in project_ids]))
            .options(joinedload(ProjectFeatureEntity.library))
            .all()
        )

        # 4. 构建结果，添加匹配的字符串信息
        # 创建library_id到matched_strings的映射
        project_strings_map = {pid: sorted(set(matched_strings), key=lambda x: len(x), reverse=True)
                               for pid, matched_strings in project_ids}

        # 为每个库添加matched_strings属性
        for project in matched_projects:
            project.matched_strings = project_strings_map[project.id]

        matched_projects = sorted(matched_projects, key=lambda x: len(project_strings_map[project.id]), reverse=True)

        return matched_projects
