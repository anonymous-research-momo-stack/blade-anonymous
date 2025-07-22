import json
import re
import sys
from datetime import datetime

from environs import Env
from loguru import logger

from evaluation.conan_benchmark.interface import Binary, Library, CompileConfig, LibraryReuse, \
    Benchmark, TestSoftware, TestBinarySuite, TestBinarySuiteStat

env = Env()
env.read_env()
logger.remove()
logger.add(sys.stderr, level="INFO")


def load_json(file_path: str) -> dict:
    """
    Load the library information from a JSON file.

    Args:
        lib_info_path (str): Path to the JSON file containing library information.

    Returns:
        dict: Parsed JSON data.
    """
    import json

    with open(file_path, 'r') as file:
        lib_info = json.load(file)

    return lib_info


import subprocess
import os
from typing import List, Dict


def is_elf_binary(file_path: str) -> bool:
    """
    使用file命令检查文件是否是ELF二进制文件
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return False

        # 1. 名称检查，.so 的是
        file_name = os.path.basename(file_path)
        if ".so" in file_name:
            return True
        # 这些都不是
        elif file_name.endswith(('.a', '.txt', '.md', '.sh', '.py', '.json')):
            return False

        # 2. 使用file命令检查文件类型
        result = subprocess.run(['file', file_path],
                                capture_output=True,
                                text=True,
                                timeout=5)

        if result.returncode != 0:
            print(f"file命令执行失败: {file_path}")
            return False

        file_output = result.stdout.strip()
        file_output = file_output.replace(file_path, '').lower()

        # 2.1 有这些关键字的都不是
        script_indicators = [
            'shell script',
            'perl script',
            'python script',
            'text executable',
            'ascii text'
        ]
        for script_type in script_indicators:
            if script_type in file_output:
                # print(f"过滤脚本文件: {os.path.basename(file_path)} -> {file_output}")
                return False

        # 2.2 有这些关键字的是
        if 'elf' in file_output:
            return True



        # 3. 不知道什么类型的，不是。
        print(f"未知文件类型, file_name: {file_name}, \n"
              f"file_path: {file_path}, \n"
              f"file_output: {file_output}")
        return False

    except subprocess.TimeoutExpired:
        print(f"file命令超时: {file_path}")
        return False
    except Exception as e:
        print(f"检查文件时出错 {file_path}: {e}")
        return False




def generate_benchmark(conan_libs_builder_output_dir, src_lib_info: dict, min_reused_lib_num: int = 1) -> List[
    TestSoftware]:
    test_software_dict = {}
    failed_find_binary_cases = set()
    for src_lib_name, src_lib_data in src_lib_info.items():
        for src_lib_ver, src_lib_ver_data in src_lib_data.items():
            for compile_config, compile_data in src_lib_ver_data.items():
                metadata_json_path = compile_data.get("metadata_json")
                if not os.path.exists(metadata_json_path):
                    continue
                metadata = load_json(metadata_json_path) if metadata_json_path else {}

                binary_info = compile_data.get("binary_info")
                real_reused_tpl_names = list(binary_info.keys())

                # 1. 源库信息
                test_software = get_test_software(metadata, src_lib_name, src_lib_ver, test_software_dict)


                # 2. reused_libraries
                library_reuses = get_library_reuses(metadata, real_reused_tpl_names, src_lib_name)
                rel_reused_lib_num = len([reuse for reuse in library_reuses if reuse.is_real_used])

                # 过滤条件1： test_suite 至少 n 个第三方库
                if rel_reused_lib_num < min_reused_lib_num:
                    continue  # Skip this test case if reused libraries are less than the minimum required


                # 3. 编译配置
                compile_config = CompileConfig(
                    conan_version=metadata.get("build_info", {}).get("conan_version", ""),
                    profile=os.path.basename(metadata.get("build_configuration", {}).get("profile", "")),
                )
                # 过滤条件2： 跳过静态链接编译的
                if "-static" in compile_config.profile:
                    continue

                # 4. 编译好的二进制文件
                binary_dict = get_target_binaries(binary_info, conan_libs_builder_output_dir, failed_find_binary_cases)

                # 过滤条件3：没有二进制测试用例的跳过。
                if not binary_dict:
                    continue

                # 5. 生成测试套件
                # 根据找到的测试用例的情况，更新reuse的测试用例覆盖情况
                for lib_reuse in library_reuses:
                    if lib_reuse.library.name in binary_dict:
                        lib_reuse.has_tc = True

                test_suite = TestBinarySuite(
                    stat=TestBinarySuiteStat(
                        total_reused_library=rel_reused_lib_num,
                        total_binaries=sum(len(binaries) for binaries in binary_dict.values()),
                        bin_binaries= sum(len([b for b in binaries if b.type == 'bin']) for binaries in binary_dict.values()),
                        lib_binaries= sum(len([b for b in binaries if b.type == 'lib']) for binaries in binary_dict.values()),
                    ),
                    library_reuses=library_reuses,
                    compile_config=compile_config,
                    binaries=binary_dict
                )


                # 6. 添加到测试软件
                test_software.test_binary_suites.append(test_suite)

    for case in failed_find_binary_cases:
        print(case)
    # 过滤掉空的
    test_softwares = [ts for ts in test_software_dict.values() if ts.test_binary_suites]
    return test_softwares

def find_target_bin(library_name: str,
                    binary_files: List[str],
                    whitelist: Dict[str, str] = None) -> List[str]:
    """
    找到匹配的主要二进制文件

    Args:
        library_name: 库名（如 "grpc", "protobuf", "openssl"）
        binary_files: 所有二进制文件名的列表（包括bin和lib目录下的）
        whitelist: 白名单字典，键为库名，值为对应的二进制文件名

    Returns:
        匹配的二进制文件名列表，如果没找到返回空列表
    """
    matches = []
    whitelist = {
        # 有信心
        'zlib': ['libz', 'libz.so.1.3.1'],
        'c-ares': ['libcares.so.2.19.4'],
        'pcre2': ['libpcre2-8.so.0.11.2'],
        'libxcrypt': ['libcrypt.so.1.1.0'],

        # 可能是
        'xz_utils': ['liblzma.so.5.4.5'],
        'util-linux-libuuid': ['libuuid.so.1.3.0'],
        'accellera-uvm-systemc': ['libuvm-systemc-1.0-beta4.so'],
        'protobuf': ['protoc-27.0.0'],

        # 基于搜索结果添加
        'aaf': ['libcom-api.so'],  # 主要的COM API库，其他组件依赖它
        'abseil': ['libabsl_base.so.2501.0.0'],  # 基础库，所有其他Abseil代码都依赖它
    }
    # 1. 在白名单中的是
    if whitelist and library_name in whitelist:
        target_files = whitelist[library_name]
        matches.extend(list(set(target_files).intersection(binary_files)))

    library_name = library_name.lower()
    # 2. 按规则匹配
    for binary_file in binary_files:

        # 提取文件名（去掉路径）
        filename = binary_file.split('/')[-1]
        filename = filename.lower()

        # 规则1: 和库的名字完全一样
        if filename == library_name:
            matches.append(binary_file)
            continue

        # 规则2: lib库名
        if filename == f"lib{library_name}":
            matches.append(binary_file)
            continue

        # 规则3: 库.so
        if filename == f"{library_name}.so":
            matches.append(binary_file)
            continue

        # 规则4: lib库.so
        if filename == f"lib{library_name}.so":
            matches.append(binary_file)
            continue

        # 规则5: 库.so.xxxx (版本号)
        pattern = f"^{re.escape(library_name)}\\.so\\."
        if re.match(pattern, filename):
            matches.append(binary_file)
            continue

        # 规则6: lib库.so.xxxx (版本号)
        pattern = f"^lib{re.escape(library_name)}\\.so\\."
        if re.match(pattern, filename):
            matches.append(binary_file)
            continue

    return list(set(matches))


def get_target_binaries(tpl_info, conan_libs_builder_output_dir, failed_cases:set):
    tpl_binaries = {}
    # 遍历所有第三方库
    for tpl_name, tpl_info in tpl_info.items():
        # 信息预处理
        tpl_info = tpl_info.get("tpl_info", {})

        tpl_name = tpl_info["tpl_name"]
        bin_bins = tpl_info.get("bin_bins", {})
        if not bin_bins:
            bin_bins = {}
        lib_bins = tpl_info.get("lib_bins", {})
        if not lib_bins:
            lib_bins = {}

        # basic info dict
        hash_to_size_dict = {}
        hash_to_path_dict = {}
        path_to_hash_dict = {}
        name_to_hash_dict = {}
        name_to_path_dict = {}
        for sha256, binary_info in {**bin_bins, **lib_bins}.items():
            binary_size = binary_info.get("size", 0)
            hash_to_size_dict[sha256] = binary_size

            binary_paths = binary_info.get("paths", [])
            hash_to_path_dict[sha256] = binary_paths[0]
            binary_paths.sort(key=lambda x: len(x), reverse=True) # 按名称长度排序

            for binary_path in binary_paths:
                # 不是二进制文件跳过。
                if not is_elf_binary(binary_path):
                    continue

                path_to_hash_dict[binary_path]  = sha256
                # name_to_hash_dict
                name = os.path.basename(binary_path)
                name_to_hash_dict[name] = sha256
                # name_to_path_dict
                name_to_path_dict[name] = binary_path
                break

        # find target binary files
        all_names = list(name_to_hash_dict.keys())

        # 直接没有二进制文件的跳过
        if not all_names:
            continue

        target_bin_names = find_target_bin(tpl_name, all_names)
        target_bin_paths = [name_to_path_dict.get(name) for name in target_bin_names if name in name_to_path_dict]

        if not target_bin_names:
            failed_cases.add(f"{tpl_name}: {all_names}")

        target_binaries = []
        for target_bin_path in target_bin_paths:
            target_bin_name = os.path.basename(target_bin_path)
            sha256 = path_to_hash_dict.get(target_bin_path, "")
            binary = Binary(
                name=target_bin_name,
                type='lib' if '.so' in target_bin_name else 'bin',
                tpl_name=tpl_name,
                rel_path=str(os.path.relpath(target_bin_path, conan_libs_builder_output_dir)),
                file_size_kb=hash_to_size_dict[sha256],
                # file_size_kb=0,
                sha256= sha256
            )
            target_binaries.append(binary)
        tpl_binaries[tpl_name] = target_binaries

    return tpl_binaries


def get_library_reuses(metadata, real_reused_tpl_names, src_lib_name):
    dependencies = metadata.get("dependencies", {}).get("dependencies", [])
    library_reuses = []
    for dep in dependencies:
        tpl_name = dep.get("name", "")
        if tpl_name == src_lib_name:
            link_type = "self"
        else:
            link_type = dep.get("link_type", "")

        reuse = LibraryReuse(
            library=Library(
                name=tpl_name,
                version=dep.get("version", "")
            ),
            is_real_used=tpl_name in real_reused_tpl_names and link_type != "header-only", # 是否是实际使用的库， 1）不是header-only 2) 有实际的库被编译
            link_type=link_type,
            level=dep.get("level", ""),
            reuse_paths=dep.get("paths", [])
        )

        library_reuses.append(reuse)
    return library_reuses


def get_test_software(metadata, src_lib_name, src_lib_ver, test_software_dict):
    if (test_software := test_software_dict.get(src_lib_name)) is None:
        source_library = metadata.get("target_library", {})
        source_library = Library(
            name=src_lib_name,
            version=src_lib_ver,
            description=source_library.get("description", ""),
            license=source_library.get("license", ""),
            homepage=source_library.get("homepage", ""),
            url=source_library.get("url", ""),
            topics=source_library.get("topics", []),
        )
        test_software_dict[src_lib_name] = test_software = TestSoftware(
            source_library=source_library,
            test_binary_suites=[]
        )
    return test_software


def main():
    # paths
    evaluation_dir = env.str("EVALUATION_DIR_PATH")

    conan_benchmark = os.path.join(evaluation_dir, "conan_benchmark")

    benchmark_meta_dir = os.path.join(conan_benchmark, "benchmark_meta")
    conan_libs_builder_output_dir = env.str("CONAN_LIBS_BUILDER_OUTPUT")

    # output
    conan_lib_info_json = os.path.join(benchmark_meta_dir, "conan_lib_info.json")
    benchmark_path = os.path.join(benchmark_meta_dir, "conan_library_benchmark.json")

    # Load library information
    lib_info = load_json(conan_lib_info_json)

    # Generate benchmark test cases
    test_software = generate_benchmark(conan_libs_builder_output_dir, lib_info)

    # Create benchmark
    benchmark = Benchmark(
        name="Conan Library Benchmark",  # CLB
        version=datetime.now().strftime("%Y%m%d%H%M%S"),
        test_software=test_software
    )


    # dump
    with open(benchmark_path, "w") as f:
        json.dump(benchmark.customer_serialize(), f, indent=4, ensure_ascii=False)

def benchmark_check():
    # paths
    evaluation_dir = env.str("EVALUATION_DIR_PATH")

    conan_benchmark = os.path.join(evaluation_dir, "conan_benchmark")

    benchmark_meta_dir = os.path.join(conan_benchmark, "benchmark_meta")

    benchmark_path = os.path.join(benchmark_meta_dir, "conan_library_benchmark.json")

    # Load library information
    benchmark = load_json(benchmark_path)

    benchmark = Benchmark.init_from_dict(benchmark)

    # stats
    benchmark.stat()


if __name__ == '__main__':
    main()
    benchmark_check()