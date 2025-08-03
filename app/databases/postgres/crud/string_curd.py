from typing import List

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert

from ..entities import StringLiteralFeatureEntity, association_project_string
from ..postgres import session_generator


def list_strings_by_project_id(project_id: int) -> List[StringLiteralFeatureEntity]:
    """
    根据库 ID 获取所有关联的字符串
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
    批量插入字符串，基于 content 的唯一约束处理重复
    """
    if not strings:
        return []

    with session_generator() as session:
        # 先插入所有字符串，忽略冲突
        stmt = insert(StringLiteralFeatureEntity).values([
            {"content": s}
            for s in strings
        ])
        stmt = stmt.on_conflict_do_nothing(index_elements=['content'])
        session.execute(stmt)

        # 查询所有字符串对象，包括已存在的
        all_literals = session.query(StringLiteralFeatureEntity).filter(
            StringLiteralFeatureEntity.content.in_(strings)
        ).all()

        return all_literals


def delete_orphaned_strings() -> int:
    """
    暂时还没用到
    删除没有任何关联的字符串
    返回删除的字符串数量
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
