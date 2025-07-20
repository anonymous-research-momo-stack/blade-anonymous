import sys

from environs import Env
from loguru import logger

env = Env()
env.read_env()
logger.remove()
logger.add(sys.stderr, level="INFO")


import dataclasses
import traceback
from dataclasses import asdict, fields
from dataclasses import dataclass
from typing import Dict, Type, Any
from typing import List

from loguru import logger


@dataclass
class Serializable:
    def customer_serialize(self) -> Dict[str, Any]:
        serialized_data = asdict(self)
        for field in fields(self):
            value = getattr(self, field.name)
            if hasattr(value, 'customer_serialize'):
                serialized_data[field.name] = value.customer_serialize()
            elif isinstance(value, list) and value and hasattr(value[0], 'customer_serialize'):
                serialized_data[field.name] = [item.customer_serialize() for item in value]
        return serialized_data

    @classmethod
    def init_from_dict(cls: Type['Serializable'], data: Dict[str, Any]) -> 'Serializable':

        init_args = {}
        for field in fields(cls):
            try:
                field_value = data.get(field.name)
                if hasattr(field.type, 'init_from_dict') and isinstance(field_value, dict):
                    init_args[field.name] = field.type.init_from_dict(field_value)
                elif (isinstance(field_value, list) and
                      field.type.__args__ and
                      hasattr(field.type.__args__[0], 'init_from_dict') and
                      all(isinstance(i, dict) for i in field_value)):
                    init_args[field.name] = [field.type.__args__[0].init_from_dict(item) for item in field_value]
                else:
                    init_args[field.name] = field_value
            except Exception as e:
                logger.error(f"Error in {cls.__name__}, field: {field.name}, type: {field.type}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise e
        return cls(**init_args)





@dataclass
class Library(Serializable):
    # meta
    name: str
    version: str
    description: str = ""
    license: str = ""
    homepage: str = ""
    url: str = ""
    topics: List[str] = dataclasses.field(default_factory=list)

    def __hash__(self):
        return hash((self.name, self.version))

    def __eq__(self, other):
        if not isinstance(other, Library):
            return NotImplemented
        return self.name == other.name and self.version == other.version

@dataclass
class LibraryReuse(Serializable):

    # library
    library:Library

    # reuse
    is_real_used: bool = True  # Whether the library is actually used in the binary
    link_type: str = "shared"  # e.g., "static", "shared"
    level: str = 1  # e.g., "local", "global"
    reuse_paths: List[str] = dataclasses.field(default_factory=list)  # Paths to the reused libraries

@dataclass
class CompileConfig(Serializable):
    conan_version:str
    profile:str

@dataclass
class Binary(Serializable):
    # under what tpl dir
    tpl_name: str


    # meta
    name: str
    type: str  # e.g., "bin", "lib"
    rel_path:str # 相对路径
    file_size_kb: float
    sha256: str

    def __hash__(self):
        return hash((self.tpl_name, self.name, self.sha256))
    def __eq__(self, other):
        if not isinstance(other, Binary):
            return NotImplemented
        return (self.tpl_name == other.tpl_name and
                self.name == other.name and
                self.sha256 == other.sha256)

@dataclass
class TestBinarySuiteStat(Serializable):
    total_reused_library:int
    total_binaries:int
    bin_binaries: int  # Number of binary files
    lib_binaries: int

@dataclass
class TestBinarySuite(Serializable):
    # stat
    stat: TestBinarySuiteStat = None

    # compile config
    compile_config: CompileConfig = None  # Compile configuration, e.g., "Release", "Debug"

    # reused_libraries
    library_reuses: List[LibraryReuse] = dataclasses.field(default_factory=list)

    # binaries
    binaries: Dict[str, List[Binary]] = dataclasses.field(default_factory=list)


@dataclass
class TestSoftware(Serializable):
    # library meta
    source_library: Library  # The source library for this test case

    test_binary_suites: List[TestBinarySuite] = dataclasses.field(default_factory=list)  # List of test binary suites


@dataclass
class Benchmark(Serializable):
    name: str
    version: str
    test_software: List[TestSoftware] = dataclasses.field(default_factory=list)