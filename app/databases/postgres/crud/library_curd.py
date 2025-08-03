from typing import List, Tuple

from loguru import logger
from sqlalchemy import func, text

from ..entities import LibraryEntity
from ..postgres import session_generator


def list_libraries(
        page: int = 1,
        page_size: int = 10
) -> Tuple[List[LibraryEntity], int]:
    """
    获取库列表，支持分页和排序

    Args:
        page: 当前页码，从1开始
        page_size: 每页数量
        sort_by: 排序字段，默认按创建时间
        sort_desc: 是否降序排序，默认True

    Returns:
        Tuple[List[LibraryEntity], int]: 返回库列表和总数

    Raises:
        SQLAlchemyError: 数据库操作错误
    """
    with session_generator() as session:
        # 构建基础查询
        query = session.query(LibraryEntity).where(
            LibraryEntity.is_feature_inserted == True
        ).order_by(LibraryEntity.id)

        # 获取总数
        total_count = query.count()

        # 分页
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # 执行查询
        libraries = query.all()

        return libraries, total_count


def count_libraries() -> int:
    with session_generator() as session:
        # 构建基础查询
        query = session.query(func.count(LibraryEntity.id)).where(
            LibraryEntity.is_feature_inserted == True
        )

        # 执行查询
        total_count = query.scalar()

        return total_count


def get_library_by_id(library_id: int) -> LibraryEntity:
    with session_generator() as session:
        library = session.get(LibraryEntity, library_id)
        return library


def list_libraries_by_name(name: str) -> List[LibraryEntity]:
    """

    :param name: the name of this library's repository
    :return:
    """
    with session_generator() as session:
        libraries = session.query(LibraryEntity).filter(LibraryEntity.name == name).all()
        return libraries



def get_library_by_repository(repository: str) -> LibraryEntity:
    """

    :param repository: the git url of this library's repository
    :return:
    """
    with session_generator() as session:
        library = session.query(LibraryEntity).filter(LibraryEntity.repository == repository).first()
        return library


def add_library(
        library: LibraryEntity,
) -> LibraryEntity:
    with session_generator() as session:
        session.add(library)
        return library


def query_largest_library_id() -> int:
    with session_generator() as session:
        result = session.query(func.max(LibraryEntity.id)).scalar()
        return result or 0


def delete_library_by_id(library_id: int) -> bool:
    """
    删除library以及它所有关联的特征（但不删除字符串）

    :param library_id:
    :return:
    """

    with session_generator() as session:
        logger.info(f"Starting to delete library with id {library_id}")

        # 检查 library 是否存在
        library = session.get(LibraryEntity, library_id)
        if not library:
            logger.info(f"Library with id {library_id} not found")
            return False
        logger.info(f"library with id {library_id} is refer to {library.name}: {library.repository}")

        project_id = library_id
        # 一次性删除所有字符串关联关系
        logger.info("Starting to delete all relationships")
        session.execute(text(f"""
            DELETE FROM association_project_string WHERE project_id ={project_id};

            DELETE FROM association_file_string 
            WHERE file_id IN (
                SELECT id FROM feature_files where project_id = {project_id}
            );

            DELETE FROM association_function_string 
            WHERE function_id IN (
                SELECT id FROM feature_functions where project_id = {project_id}
            );
        """), {"library_id": library_id})
        logger.info("Finished deleting all relationships")

        # 2. 直接批量删除 functions
        logger.info("Starting to delete functions")
        session.execute(text(f"""
            DELETE FROM feature_functions 
            WHERE project_id = {project_id};
        """))

        # 3. 直接批量删除 files
        logger.info("Starting to delete files")
        session.execute(text(f"""
            DELETE FROM feature_files 
            WHERE project_id = {project_id};
        """))

        # 4. 直接批量删除 project
        logger.info("Starting to delete project")
        session.execute(text(f"""
            DELETE FROM feature_projects 
            WHERE id = {project_id};
        """))

        # 5. 最后删除 library
        logger.info("Starting to delete library")
        session.execute(text(f"""
            DELETE FROM meta_libraries 
            WHERE id = {library_id};
        """))

        logger.info("Delete ALL Done!")

        return True
