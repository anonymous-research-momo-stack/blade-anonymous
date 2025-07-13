import os
from typing import List, Optional
from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, Float, Sequence, create_engine, ARRAY, \
    Table, Index, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship, declared_attr
from sqlalchemy.sql import func
from loguru import logger

from app.config import settings

Base = declarative_base()


# 创建时间戳 Mixin
class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


# 创建关联表
association_function_string = Table(
    'association_function_string',
    Base.metadata,
    Column('function_id', BigInteger, ForeignKey('feature_functions.id')),
    Column('string_id', BigInteger, ForeignKey('feature_string_literals.id')),
    Index('ix_function_string_composite', 'function_id', 'string_id', unique=True)
)

association_file_string = Table(
    'association_file_string',
    Base.metadata,
    Column('file_id', BigInteger, ForeignKey('feature_files.id')),
    Column('string_id', BigInteger, ForeignKey('feature_string_literals.id')),
    Index('ix_file_string_composite', 'file_id', 'string_id', unique=True)
)

association_project_string = Table(
    'association_project_string',
    Base.metadata,
    Column('project_id', BigInteger, ForeignKey('feature_projects.id')),
    Column('string_id', BigInteger, ForeignKey('feature_string_literals.id')),
    Index('ix_project_string_composite', 'project_id', 'string_id', unique=True)
)


# Features to Match
class StringLiteralFeatureEntity(TimestampMixin, Base):
    __tablename__ = 'feature_string_literals'
    id = Column(BigInteger, Sequence('feature_string_literals_id_seq'), primary_key=True, nullable=False)
    content = Column(Text, unique=True)

    # 包含该字符串的函数
    functions = relationship("FunctionFeatureEntity",
                             secondary=association_function_string,
                             back_populates="string_literals")

    # 包含该字符串的文件
    files = relationship("FileFeatureEntity",
                         secondary=association_file_string,
                         back_populates="string_literals")

    # 包含该字符串的library
    projects = relationship("ProjectFeatureEntity",
                            secondary=association_project_string,
                            back_populates="string_literals")


class FunctionFeatureEntity(TimestampMixin, Base):
    __tablename__ = 'feature_functions'
    id = Column(BigInteger, Sequence('feature_functions_id_seq'), primary_key=True, nullable=False)

    name = Column(String(255), index=True)
    start_line = Column(BigInteger)
    end_line = Column(BigInteger)
    file_path = Column(String(1024))
    distinct_string_num = Column(BigInteger)
    source_codes = Column(ARRAY(Text))

    # 所属 file, project, library
    file_id = Column(BigInteger, ForeignKey('feature_files.id'), index=True)
    file = relationship("FileFeatureEntity", back_populates="functions")

    project_id = Column(BigInteger, ForeignKey('feature_projects.id'), index=True)
    project = relationship("ProjectFeatureEntity", back_populates="functions")

    # features
    string_literals = relationship("StringLiteralFeatureEntity", secondary=association_function_string,
                                   back_populates="functions")


class FileFeatureEntity(TimestampMixin, Base):
    __tablename__ = 'feature_files'
    id = Column(BigInteger, Sequence('feature_files_id_seq'), primary_key=True, nullable=False)

    name = Column(String(255), index=True)
    extension = Column(String(255))
    path = Column(String(512))
    file_size_kb = Column(Float)
    function_num = Column(BigInteger)
    distinct_string_num = Column(BigInteger)
    extraction_succeed = Column(Boolean, default=True)
    extraction_log = Column(Text)

    # 所属project, library
    project_id = Column(BigInteger, ForeignKey('feature_projects.id'), index=True)
    project = relationship("ProjectFeatureEntity", back_populates="files")

    # features
    functions = relationship("FunctionFeatureEntity", back_populates="file")
    string_literals = relationship("StringLiteralFeatureEntity", secondary=association_file_string,
                                   back_populates="files")


class ProjectFeatureEntity(TimestampMixin, Base):
    __tablename__ = 'feature_projects'

    id = Column(BigInteger, Sequence('feature_projects_id_seq'), primary_key=True, nullable=False)

    name = Column(String(255), index=True)
    project_size_mb = Column(Float)
    total_src_file = Column(BigInteger)
    failed_src_file = Column(BigInteger)
    exception_src_file = Column(BigInteger)
    function_count = Column(BigInteger)
    distinct_string_count = Column(BigInteger)
    extraction_succeed = Column(Boolean, default=True)
    extraction_log = Column(Text)

    # library
    library_id = Column(BigInteger, ForeignKey('meta_libraries.id'), unique=True, index=True)
    library = relationship("LibraryEntity", back_populates="project", uselist=False)

    # file
    files = relationship("FileFeatureEntity", back_populates="project")

    # functions
    functions = relationship("FunctionFeatureEntity", back_populates="project")

    # strings
    string_literals = relationship("StringLiteralFeatureEntity",
                                   secondary=association_project_string,
                                   back_populates="projects")


# Library
class LibraryEntity(TimestampMixin, Base):
    __tablename__ = 'meta_libraries'
    __table_args__ = (
        UniqueConstraint('name', 'vendor', name='uix_library_name_vendor'),
    )
    id = Column(BigInteger, Sequence('meta_libraries_id_seq'), primary_key=True, nullable=False)

    # basic info
    name = Column(String(255), nullable=False, index=True)
    vendor = Column(String(255), nullable=False, index=True)
    repository = Column(String(255), nullable=False, index=True)

    description = Column(Text)  # Description Generated from GPT4o
    repo_description = Column(Text)  # Github Repo Description

    # status
    is_source_code_downloaded = Column(Boolean, default=True, index=True)
    is_feature_extracted = Column(Boolean, default=True, index=True)
    is_feature_inserted = Column(Boolean, default=True, index=True)

    # note
    note = Column(Text)

    # features
    project = relationship("ProjectFeatureEntity", back_populates="library", uselist=False)


def create_all_tables():
    """
    创建所有表
    """
    # 创建数据库引擎

    engine = create_engine(
        url=settings.MAIN_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=-1,
        pool_recycle=3600,
    )

    # 删除所有
    Base.metadata.drop_all(engine)

    # 创建所有定义的表
    Base.metadata.create_all(engine)

    logger.debug("Tables created successfully.")


if __name__ == '__main__':
    create_all_tables()
