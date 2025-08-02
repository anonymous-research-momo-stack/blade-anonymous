import os
from datetime import datetime
from typing import Dict, List

from evaluation.general_benchmarks.interface import Benchmark, BenchmarkNote

# 在类外部定义别名字典
# 从新数据中提取的真正别名关系
ALIAS_DICT = {
    # lib前缀差异
    "libalsa": ["alsa-lib"],
    "libuuid": ["util-linux"],
    "libverto": ["verto"],
    "libaom-av1": ["aom", "libaom"],
    "libx264": ["x264"],
    "libsquish": ["squish"],
    "libmount": ["util-linux"],
    "libgettext": ["gettext"],
    "pupnp": ["libupnp"],
    "aws-libfabric": ["libfabric"],
    "librasterlite": ["RasterLite"],
    "libspatialite": ["SpatiaLite"],
    "b64": ["libb64"],
    "base64": ["libbase64"],
    "libsndio": ["sndio"],
    "libmp3lame": ["LAME"],
    "vorbis": ["libvorbis"],
    "ogg": ["libogg"],
    "iqa": ["libiqa"],
    "libzen": ["ZenLib"],
    "cmaes": ["libcmaes"],

    # 版本/实现差异
    "libjpeg": ["libjpeg-turbo"],
    "util-linux-libuuid": ["util-linux", "libuuid"],
    "dd-opentracing-cpp": ["dd-opentracing", "OpenTracing C++"],
    "tensorflow-lite": ["TensorFlow Lite", "TensorFlow"],
    "mozjpeg": ["libjpeg-turbo"],

    # 命名风格差异
    "libsigcpp": ["libsigc++"],
    "xz_utils": ["XZ Utils", "xz"],
    "open-simulation-interface": ["Open Simulation Interface"],
    "lzma_sdk": ["LZMA SDK"],
    "editline": ["libedit"],
    "sdbus-cpp": ["sdbus-c++"],
    "openddl-parser": ["OpenDDLParser"],
    "voropp": ["Voro++"],
    "openal-soft": ["OpenAL Soft"],
    "llvm-core": ["LLVM"],
    "llvm-openmp": ["OpenMP"],
    "bullet3": ["Bullet"],
    "marisa": ["marisa-trie"],
    "sqlite3": ["SQLite"],
    "sassc": ["LibSass"],

    # 包名差异 - COIN-OR项目
    "coin-cgl": ["Cgl"],
    "coin-utils": ["CoinUtils"],
    "coin-osi": ["Osi"],
    "coin-clp": ["Clp"],
    "coin-lemon": ["lemon"],

    # 下划线与连字符差异
    "http_parser": ["http-parser"],
    "libfdk_aac": ["fdk-aac"],
    "hdrhistogram-c": ["HdrHistogram_c"],
    "foonathan-memory": ["foonathan_memory"],

    # 项目与库名差异
    "tng": ["tng_io"],
    "miniscript": ["MiniScript-cpp"],
    "embree3": ["embree"],
    "odbc": ["unixODBC"],
    "libtool": ["libltdl"],
    "abseil": ["abseil-cpp"],
    "nodejs": ["Node.js"],
    "intel-ipsec-mb": ["IPSec_MB"],
    "andreasbuhr-cppcoro": ["cppcoro"],
    "grpc-proto": ["gRPC"],


    # 特殊项目命名
    "tiny-aes-c": ["TinyAES"],
    "rapidyaml": ["ryml"],
    "jbig": ["jbigkit"],
    "libelfin": ["libelf++"],
    "lcms": ["lcms2"],
    "json-schema-validator": ["nlohmann/json-schema-validator", "nlohmann_json_schema_validator"],
    "msdf-atlas-gen": ["msdfgen"],
    "opengrm": ["OpenGrm Thrax", "Thrax"],

    # Azure SDK 系列
    "azure-storage-cpp": ["Azure Storage Client Library for C++"],

    # MariaDB 连接器
    "mariadb-connector-cpp": ["MariaDB Connector/C++"],
    "mariadb-connector-c": ["MariaDB Connector/C"],

    # 有意义的别名差异
    "opencv": ["cv2"],
    "tensorflow": ["tf"],
    "boost": ["boost-libs"],
    "eigen": ["Eigen3", "libeigen"],
    "jsoncpp": ["json", "JsonCpp"],
    "protobuf": ["protoc", "Protocol Buffers"],
    "zlib": ["libz", "zlib-dev"],
    "curl": ["libcurl"],
}


class BenchmarkUpdator:

    def __init__(self, benchmark_json_path: str):
        """
        初始化 BenchmarkUpdator

        Args:
            benchmark_json_path: benchmark JSON 文件的路径
        """
        self.benchmark_json_path = benchmark_json_path
        self.benchmark = Benchmark.load_from_json_file(benchmark_json_path)

    def _normalize_name(self, name: str) -> str:
        """将名称标准化为小写，用于比较"""
        return name.lower().strip()

    def _is_duplicate_alias(self, existing_names: List[str], new_alias: str) -> bool:
        """
        检查新别名是否已存在（忽略大小写）

        Args:
            existing_names: 已有的名称列表
            new_alias: 要检查的新别名

        Returns:
            True 如果已存在，False 如果不存在
        """
        normalized_new = self._normalize_name(new_alias)
        normalized_existing = [self._normalize_name(name) for name in existing_names]
        return normalized_new in normalized_existing

    def update(self):
        """
        更新 benchmark 中所有库的别名，并保存到新文件

        Returns:
            str: 新保存文件的路径
        """
        update_log = []  # 记录所有更新操作
        total_updates = 0

        # 遍历所有测试用例
        for test_case in self.benchmark.test_cases:
            # 遍历每个测试用例中的重用库
            for reused_lib in test_case.reused_libraries:
                lib_name = reused_lib.name
                normalized_lib_name = self._normalize_name(lib_name)

                # 检查是否在别名字典中
                matching_key = None
                for key in ALIAS_DICT.keys():
                    if self._normalize_name(key) == normalized_lib_name:
                        matching_key = key
                        break

                if matching_key:
                    # 获取该库的别名列表
                    aliases = ALIAS_DICT[matching_key]

                    # 准备当前库的所有现有名称（包括主名称和已有别名）
                    existing_names = [lib_name]
                    if reused_lib.other_names:
                        existing_names.extend(reused_lib.other_names)
                    else:
                        reused_lib.other_names = []

                    # 添加新别名（避免重复）
                    added_aliases = []
                    for alias in aliases:
                        if not self._is_duplicate_alias(existing_names, alias):
                            reused_lib.other_names.append(alias)
                            existing_names.append(alias)  # 更新现有名称列表
                            added_aliases.append(alias)

                    # 如果有新别名被添加，记录到日志
                    if added_aliases:
                        update_log.append(f"Library '{lib_name}' added aliases: {', '.join(added_aliases)}")
                        total_updates += 1

        # 如果有更新，添加到 benchmark notes
        if update_log:
            update_message = f"Updated aliases for {total_updates} libraries:\n" + "\n".join(update_log)
            note = BenchmarkNote(message=update_message)
            self.benchmark.notes.append(note)

        # 生成新文件名（带时间戳）
        new_file_path = self._generate_timestamped_filename()

        # 保存到新文件
        self.benchmark.dump_to_json_file(new_file_path)

        return new_file_path

    def _generate_timestamped_filename(self) -> str:
        """
        生成带时间戳的新文件名

        Returns:
            str: 新文件路径
        """
        # 获取当前时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        # 分离文件路径和扩展名
        dir_path = os.path.dirname(self.benchmark_json_path)
        file_name = os.path.basename(self.benchmark_json_path)
        name_without_ext, ext = os.path.splitext(file_name)

        # 生成新文件名
        new_file_name = f"{name_without_ext}_{timestamp}{ext}"
        new_file_path = os.path.join(dir_path, new_file_name)

        return new_file_path

    def preview_updates(self) -> Dict[str, List[str]]:
        """
        预览将要进行的更新操作，不实际修改数据

        Returns:
            Dict[str, List[str]]: 字典，键为库名，值为将要添加的别名列表
        """
        preview = {}

        for test_case in self.benchmark.test_cases:
            for reused_lib in test_case.reused_libraries:
                lib_name = reused_lib.name
                normalized_lib_name = self._normalize_name(lib_name)

                # 检查是否在别名字典中
                matching_key = None
                for key in ALIAS_DICT.keys():
                    if self._normalize_name(key) == normalized_lib_name:
                        matching_key = key
                        break

                if matching_key:
                    aliases = ALIAS_DICT[matching_key]

                    # 准备当前库的所有现有名称
                    existing_names = [lib_name]
                    if reused_lib.other_names:
                        existing_names.extend(reused_lib.other_names)

                    # 找出将要添加的新别名
                    new_aliases = []
                    for alias in aliases:
                        if not self._is_duplicate_alias(existing_names, alias):
                            new_aliases.append(alias)

                    if new_aliases:
                        preview[lib_name] = new_aliases

        return preview


if __name__ == '__main__':
    benchmark_json_path ="/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark.json"
    updator = BenchmarkUpdator(benchmark_json_path)

    # 预览将要进行的更新
    preview = updator.preview_updates()
    print("Preview of updates:")
    for lib, aliases in preview.items():
        print(f"{lib}: {', '.join(aliases)}")

    # 执行更新并保存到新文件
    new_file_path = updator.update()
    print(f"Updated benchmark saved to: {new_file_path}")