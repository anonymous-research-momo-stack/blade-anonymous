from typing import List

from sqlalchemy import func

from app.tpl_detection.databases.postgres_new.entities import StringFeature, StringToLibrary, Library
from app.tpl_detection.databases.postgres_new.postgres import session_generator


def list_libraries_by_strings(strings: List[str], min_match_num: int = 5):
    """
    查询与给定字符串列表至少有指定数量交集的库

    Args:
        strings: 要查询的字符串列表
        min_match_num: 最小匹配字符串数量，默认5

    Returns:
        匹配的库列表，每个库对象包含匹配的字符串列表
    """
    with session_generator() as session:
        # 1. 首先查询匹配的字符串ID和内容
        string_features = (
            session.query(StringFeature.id, StringFeature.string_value)
            .filter(StringFeature.string_value.in_(strings))
            .all()
        )

        if not string_features:
            return []

        # 2. 查询字符串-库关联关系，并找到满足条件的库ID
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

        # 3. 查询匹配的库信息
        matched_libraries = (
            session.query(Library)
            .filter(Library.id.in_([lib_id for lib_id, _ in library_matches]))
            .all()
        )

        # 4. 构建结果，添加匹配的字符串信息
        # 创建library_id到matched_strings的映射
        library_strings_map = {
            lib_id: sorted(set(matched_strings), key=lambda x: len(x), reverse=True)
            for lib_id, matched_strings in library_matches
        }

        # 为每个库添加matched_strings属性
        for library in matched_libraries:
            library.matched_strings = library_strings_map[library.id]

        # 按匹配字符串数量排序
        matched_libraries = sorted(
            matched_libraries, 
            key=lambda x: len(library_strings_map[x.id]), 
            reverse=True
        )

        return matched_libraries