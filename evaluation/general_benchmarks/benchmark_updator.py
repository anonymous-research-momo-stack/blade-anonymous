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

# SCA组件检测结果别名映射字典
# 用于将检测到的组件名称映射到标准的ground truth名称
alias_mapping_1 = {
    "gmp": [
        "GNU Multiple Precision Arithmetic Library"
    ],
    "boost": [
        "Boost C++ Libraries"
    ],
    "libalsa": [
        "ALSA"
    ],
    "azure-sdk-for-cpp": [
        "Azure SDK Core Library",
        "Azure SDK for C++"
    ],
    "libcurl": [
        "curl"
    ],
    "expat": [
        "libexpat"
    ],
    "coin-cgl": [
        "COIN-OR Cgl"
    ],
    "coin-utils": [
        "COIN-OR CoinUtils"
    ],
    "coin-osi": [
        "COIN-OR Open Solver Interface (OSI)"
    ],
    "coin-clp": [
        "COIN-OR Clp"
    ],
    "tiny-aes-c": [
        "tiny-AES"
    ],
    "zstd": [
        "Zstandard"
    ],
    "jbig": [
        "JBIG-KIT"
    ],
    "libunistring": [
        "GNU libunistring"
    ],
    "libmysqlclient": [
        "mysql"
    ],
    "gtest": [
        "googletest"
    ],
    "tree-sitter-cpp": [
        "tree-sitter"
    ],
    "libaom-av1": [
        "AOMedia Video 1 (AV1) Codec Library",
        "AOMedia Video 1 (libaom)"
    ],
    "acl": [
        "libacl"
    ],
    "cminpack": [
        "MINPACK"
    ],
    "cgif": [
        "libcgif"
    ],
    "libselinux": [
        "selinux"
    ],
    "dd-opentracing-cpp": [
        "Datadog OpenTracing"
    ],
    "libgettext": [
        "GNU gettext"
    ],
    "cyrus-sasl": [
        "Cyrus SASL"
    ],
    "mtdev": [
        "libmtdev"
    ],
    "twitch-native-ipc": [
        "Twitch IPC Library"
    ],
    "mbedtls": [
        "mbed TLS",
        "mbed_tls"
    ],
    "libtool": [
        "GNU libtool"
    ],
    "libx265": [
        "x265"
    ],
    "compute_library": [
        "computelibrary"
    ],
    "cpuinfo": [
        "libcpuinfo"
    ],
    "libfdk_aac": [
        "Fraunhofer FDK AAC"
    ],
    "skyr-url": [
        "libskyr"
    ],
    "hdrhistogram-c": [
        "HDR Histogram"
    ],
    "cpprestsdk": [
        "C++ REST SDK"
    ],
    "gdk-pixbuf": [
        "GDK Pixbuf"
    ],
    "log4cpp": [
        "log4cpp-log4cpp"
    ],
    "miniupnpc": [
        "miniupnp"
    ],
    "mdnsresponder": [
        "libdnssd"
    ],
    "librdata": [
        "rdata"
    ],
    "fftw": [
        "fftw3"
    ],
    "fast-cdr": [
        "Fast CDR"
    ],
    "librttopo": [
        "RTTopo"
    ],
    "librasterlite": [
        "RasterLite2"
    ],
    "libsystemd": [
        "systemd"
    ],
    "r8brain-free-src": [
        "r8brain"
    ],
    "libnuma": [
        "numactl"
    ],
    "bdwgc": [
        "Boehm-Demers-Weiser Garbage Collector"
    ],
    "libcvd": [
        "CVD"
    ],
    "tree-sitter-cql": [
        "tree-sitter"
    ],
    "xapian-core": [
        "xapian"
    ],
    "tree-sitter-c": [
        "Tree-sitter",
        "tree-sitter"
    ],
    "alac": [
        "libalac"
    ],
    "antlr4-cppruntime": [
        "antlr4"
    ],
    "paho-mqtt-c": [
        "Eclipse Paho MQTT C Client",
        "Eclipse Paho MQTT C Client Library"
    ],
    "openddl-parser": [
        "OpenDDL Parser"
    ],
    "tidy-html5": [
        "tidy"
    ],

    "libpq": [
        "postgres",
        "postgresql",
    ],
    "intel-ipsec-mb": [
        "Intel Multi-Buffer Crypto Library"
    ],
    "open62541pp": [
        "open62541"
    ],
    "liblsl": [
        "Lab Streaming Layer"
    ],
    "backward-cpp": [
        "libbackward"
    ],
    "clickhouse-cpp": [
        "ClickHouse C++ Client Library"
    ],
    "foxglove-websocket": [
        "Foxglove WebSocket"
    ],
    "llvm-openmp": [
        "LLVM OpenMP",
        "LLVM OpenMP Runtime",
        "LLVM OpenMP Runtime Library"
    ],
    "tgc": [
        "Tiny Garbage Collector"
    ],
    "libsersi": [
        "SERSI"
    ],
    "bullet3": [
        "Bullet Physics",
        "Bullet Physics SDK"
    ],
    "freealut": [
        "OpenAL Utility Toolkit",
        "OpenAL Utility Toolkit (ALUT)"
    ],
    "arcus": [
        "libarcus"
    ],
    "llvm-openmp": [
        "llvm"
    ],
    "cryptopp": [
        "Crypto++"
    ],
    "cryptopp-pem": [
        "Crypto++"
    ],
    "opencore-amr": [
        "OpenCORE AMR"
    ],
    "tgbot": [
        "libTgBot",
        "tgbot-cpp"
    ],
    "jxrlib": [
        "JPEG XR",
        "JPEG XR Reference Software"
    ],
    "pro-mdnsd": [
        "mdnsd"
    ],
    "dfp": [
        "Decimal Floating-Point Math Library (ddfp)",
        "Intel Decimal Floating-Point Math Library"
    ],
    "i2c-tools": [
        "libi2c"
    ],
    "libavrocpp": [
        "Apache Avro C++"
    ],
    "dbus": [
        "D-Bus"
    ],
    "poshlib": [
        "POSH",
        "posh"
    ],
    "stdgpu": [
        "libstdgpu"
    ],
    "serial": [
        "libserial"
    ],
    "theora": [
        "libtheora"
    ],
    "cspice": [
        "NAIF SPICE Toolkit",
        "SPICE Toolkit"
    ],
    "tcsbank-uri-template": [
        "liburitemplate-cpp"
    ],
    "fastnoise2": [
        "FastNoise"
    ],
    "mongo-c-driver": [
        "MongoDB C Driver"
    ],
    "libsvtav1": [
        "SVT-AV1"
    ],
    "lightpcapng": [
        "liblight_pcapng",
        "light",
        "light_pcapng"
    ],
    "c-blosc": [
        "Blosc",
        "c-blosc2"
    ],
    "svtjpegxs": [
        "SVT-JPEG XS"
    ],
    "binutils": [
        "GNU Binutils"
    ],
    "vcglib": [
        "VCG Library"
    ],
    "hexl": [
        "Intel HEXL"
    ],
    "krb5": [
        "MIT Kerberos"
    ],
    "tidwall-neco": [
        "neco"
    ],
    "sentry-crashpad": [
        "crashpad"
    ],
    "drflac": [
        "dr_flac",
        "dr_libs"
    ],
    "itk": [
        "Insight Segmentation and Registration Toolkit (ITK)"
    ],
    "dnet": [
        "libdnet"
    ],
    "rvo2": [
        "RVO"
    ],
    "llnl-units": [
        "libunits"
    ],
    "libstudxml": [
        "studxml"
    ],
    "s2geometry": [
        "S2 Geometry Library"
    ],
    "baical-p7": [
        "P7",
        "P7 Telemetry Framework"
    ],
    "libnghttp2": [
        "nghttp2"
    ],
    "crc32c": [
        "libcrc32c"
    ],
    "functions-framework-cpp": [
        "Google Functions Framework C++"
    ],
    "cose-c": [
        "libcose-c"
    ],
    "whisper-cpp": [
        "Whisper",
        "whisper"
    ],
    "id3v2lib": [
        "libid3v2"
    ],
    "hazelcast-cpp-client": [
        "Hazelcast C++ Client"
    ],
    "openmpi": [
        "Open MPI",
        "mpi"
    ],
    "dsp-filters": [
        "DSPFilters"
    ],
    "llama-cpp": [
        "LLaMA",
        "llama.cpp"
    ],
    "aws-lambda-cpp": [
        "AWS Lambda Runtime",
        "AWS Lambda Runtime Interface Client"
    ],
    "libxmlpp": [
        "libxml++"
    ],
    "capnproto": [
        "Cap'n Proto"
    ],
    "systemc-cci": [
        "CCI",
        "CCI API"
    ],
    "cnats": [
        "NATS C Client",
        "NATS C Client Library"
    ],
    "ouster_sdk": [
        "Ouster SDK"
    ],
    "ftjam": [
        "Jam"
    ],
    "clipper": [
        "libpolyclipping",
        "polyclipping"
    ],
    "drwav": [
        "dr_wav"
    ],
    "semver.c": [
        "libsemver.c"
    ],
    "lksctp-tools": [
        "libsctp"
    ],
    "libmad": [
        "MAD"
    ],
    "open-dis-cpp": [
        "OpenDIS"
    ],
    "chipmunk2d": [
        "Chipmunk",
        "Chipmunk 2D"
    ],
    "opencl-icd-loader": [
        "Khronos OpenCL",
        "OpenCL"
    ],
    "tree-sitter-sql": [
        "Tree-sitter"
    ],
    "discount": [
        "libmarkdown"
    ],
    "chunkio": [
        "libchunkio"
    ],
    "librhash": [
        "rhash"
    ],
    "cassandra-cpp-driver": [
        "DataStax C/C++ Driver for Apache Cassandra"
    ],
    "gobject-introspection": [
        "GObject Introspection"
    ],
    "fastgltf": [
        "libfastgltf"
    ],
    "libcheck": [
        "check"
    ],
    "tcp-wrappers": [
        "TCP Wrappers"
    ],
    "wasm-micro-runtime": [
        "iwasm"
    ],
    "mppp": [
        "MP++",
        "libmp++"
    ],
    "paho-mqtt-cpp": [
        "Eclipse Paho MQTT C++ Client Library"
    ],
    "tinkerforge-bindings": [
        "Tinkerforge Bindings"
    ],
    "asyncplusplus": [
        "async++"
    ],
    "rg-etc1": [
        "librg",
        "librg_etc1"
    ],
    "xlsxio": [
        "libxlsxio"
    ],
    "onnxruntime": [
        "ONNX Runtime",
        "onnx"
    ],
    "tmx": [
        "libtmx"
    ],
    "drmp3": [
        "dr_libs",
        "dr_mp3"
    ],
    "kmod": [
        "libkmod"
    ],
    "physfs": [
        "PhysicsFS"
    ],
    "sentry-native": [
        "Sentry Native SDK"
    ],
    "matio": [
        "libmatio"
    ],
    "etc2comp": [
        "EtcLib"
    ],
    "lely-core": [
        "Lely CANopen Library",
        "Lely CANopen Stack"
    ],
    "level-zero": [
        "Intel oneAPI Level Zero",
        "Level Zero",
        "oneAPI Level Zero"
    ],
    "zmarok-semver": [
        "libsemver"
    ],
    "very-simple-smtps": [
        "libsmtp_lib"
    ],
    "aws-kvs-pic": [
        "Amazon Kinesis Video Streams SDK"
    ],
    "accellera-uvm-systemc": [
        "SystemC UVM",
        "systemc"
    ],
    "kealib": [
        "Kea"
    ],
    "foxglove-schemas-protobuf": [
        "Foxglove"
    ],
    "nmea": [
        "libnmea"
    ],
    "recastnavigation": [
        "Recast Navigation"
    ],
    "mongo-cxx-driver": [
        "MongoDB C++ Driver"
    ],
    "p7zip": [
        "7-Zip"
    ],
    "isa-l": [
        "Intel ISA-L"
    ],
    "libbasisu": [
        "Basis Universal"
    ],
    "libb2": [
        "BLAKE2"
    ],
    "glbinding": [
        "libglbinding"
    ],
    "libdb": [
        "Berkeley DB"
    ],
    "sbp": [
        "libsbp"
    ],
    "libmagic": [
        "file"
    ],
    "bigint": [
        "libbigint"
    ],
    "mysql-connector-cpp": [
        "MySQL Connector/C++",
        "mysql"
    ],
    "ceres-solver": [
        "Ceres Solver"
    ],
    "djinni-support-lib": [
        "Djinni"
    ],
    "qr-code-generator": [
        "qrcodegen"
    ],
    "fast-dds": [
        "Fast DDS",
        "Fast RTPS"
    ],
    "mpdecimal": [
        "libmpdec"
    ],
    "kissfft": [
        "KISS FFT"
    ],
    "opusfile": [
        "libopusfile"
    ],
    "vectorscan": [
        "hyperscan"
    ],
    "jpeg-compressor": [
        "jpge"
    ],
    "bacnet-stack": [
        "BACnet Stack"
    ],
    "libfuse": [
        "FUSE"
    ],
    "pmp": [
        "libpmp"
    ],
    "userspace-rcu": [
        "Userspace RCU",
        "Userspace RCU (liburcu)"
    ],
    "eudev": [
        "libudev"
    ]
}

alias_mapping_2 = {
    "libfdk_aac": ["fdk-aac"],
    "paho-mqtt-c": ["paho.mqtt.c"],
    "taocpp-taopq": ["taocpp/taopq"],
    "json-schema-validator": ["nlohmann_json_schema_validator"],
    "sqlite3": ["SQLite"],
    "nodejs": ["Node.js"],
    "azure-storage-cpp": ["Azure Storage Client Library for C++"],
    "libspatialite": ["SpatiaLite"],
    "opengrm": ["Thrax", "OpenGrm Thrax"],
    "onetbb": ["tbb"],
    "libnl": ["libnl3"],
    "cmaes": ["libcmaes"]
}
for update_dict in [alias_mapping_1, alias_mapping_2]:
    for k,v in update_dict.items():
        if k not in ALIAS_DICT:
            ALIAS_DICT[k] = v
        else:
            ALIAS_DICT[k].extend(v)
            ALIAS_DICT[k] = list(set(ALIAS_DICT[k]))  # 去重


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

        # 去除重复的库
        self.benchmark.test_cases = list({tc.test_binary.sha256: tc for tc in self.benchmark.test_cases}.values())


        # 进行统计
        self.benchmark.stat()

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

                # 检查github链接的仓库名称是否在是名称，如果不是，要添加到别名
                if reused_lib.repository and 'github' in reused_lib.repository:
                    repo_link = reused_lib.repository
                    if repo_link.endswith('/'):
                        repo_link = repo_link[:-1]
                    if repo_link.endswith('.git'):
                        repo_link = repo_link[:-4]
                    repo_name = repo_link.split('/')[-1]

                    existing_names = [lib_name]
                    if reused_lib.other_names:
                        existing_names.extend(reused_lib.other_names)

                    if not self._is_duplicate_alias(existing_names, repo_name):
                        if lib_name in preview:
                            if repo_name not in preview[lib_name]:
                                preview[lib_name].append(repo_name)
                        else:
                            preview[lib_name] = [repo_name]
        return preview

"""
1. **任务目标**：帮你创建一个映射字典，解决SCA组件检测中的名称匹配问题

2. **具体工作**：
   - 你会分批次给我一些案例
   - 每个案例包含：detected names（检测结果）、ground_truth names（标准答案）、以及当前的tp/fp/fn分组情况
   - 我需要识别出那些**实际是正确的检测结果，但因为名称写法不同而被误判的情况**

3. **输出格式**：
   ```python
   {
       "groundtruth_name": ["实际正确的别名1", "实际正确的别名2", ...]
   }
   ```

4. **注意事项**：
   - 大小写差异你会自己处理，我不用考虑
   - 每次只处理你给出的那一批次案例
   - 重点是找出那些本质上是同一个组件但名称表达不同的情况

现在可以给我第一批案例了！
"""
if __name__ == '__main__':
    benchmark_json_path ="/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark_20250806_1524.json"
    updator = BenchmarkUpdator(benchmark_json_path)

    # 预览将要进行的更新
    preview = updator.preview_updates()
    print("Preview of updates:")
    for lib, aliases in preview.items():
        print(f"{lib}: {', '.join(aliases)}")

    # 执行更新并保存到新文件
    new_file_path = updator.update()
    print(f"Updated benchmark saved to: {new_file_path}")