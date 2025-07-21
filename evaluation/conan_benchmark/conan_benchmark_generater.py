import json
import os
import sys
from datetime import datetime
from typing import List

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

        # 使用file命令检查文件类型
        result = subprocess.run(['file', file_path],
                                capture_output=True,
                                text=True,
                                timeout=5)

        if result.returncode != 0:
            print(f"file命令执行失败: {file_path}")
            return False

        file_output = result.stdout.strip()
        file_output = file_output.replace(file_path, '').lower()
        # 额外检查：排除明确的脚本类型
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

        # 只要包含ELF就认为是二进制文件
        if 'elf' in file_output:
            return True



        # 如果不是ELF也不是明确的脚本，打印警告但保留
        print(f"未知文件类型: {os.path.basename(file_path)} -> {file_output}, 已过滤")
        return False

    except subprocess.TimeoutExpired:
        print(f"file命令超时: {file_path}")
        return False
    except Exception as e:
        print(f"检查文件时出错 {file_path}: {e}")
        return False

def generate_benchmark(conan_libs_builder_output_dir, src_lib_info: dict, min_reused_lib_num: int = 3) -> List[
    TestSoftware]:
    test_software_dict = {}
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
                if (test_software:= test_software_dict.get(src_lib_name)) is None:
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

                    # 2. 复用的第三方组件

                # 2. reused_libraries
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
                        is_real_used=tpl_name in real_reused_tpl_names and link_type != "header-only",
                        link_type=link_type,
                        level=dep.get("level", ""),
                        reuse_paths=dep.get("paths", [])
                    )

                    library_reuses.append(reuse)

                rel_reused_lib_num = len([reuse for reuse in library_reuses if reuse.is_real_used])


                # 3. 编译配置
                compile_config = CompileConfig(
                    conan_version=metadata.get("build_info", {}).get("conan_version", ""),
                    profile=os.path.basename(metadata.get("build_configuration", {}).get("profile", "")),
                )


                # 4. 编译好的二进制文件
                binary_dict = {}
                for tpl_name, tpl_data in binary_info.items():
                    tpl_info = tpl_data.get("tpl_info")

                    # 找到所有路径
                    bin_bin_paths = {}
                    if tpl_info.get("bin_bins", {}):
                        for sha256, paths in tpl_info.get("bin_bins", {}).items():
                            paths = [path for path in paths if is_elf_binary(path)]  # 需要验证是二进制文件，不然有很多的脚本文件。
                            if paths:
                                bin_bin_paths[sha256] = paths

                    lib_bin_paths = tpl_info.get("lib_bins", {})
                    bin_paths = {}
                    if bin_bin_paths:
                        bin_paths.update(bin_bin_paths)
                    if lib_bin_paths:
                        bin_paths.update(lib_bin_paths)

                    # 构成 Binary 对象
                    binaries = []
                    for bin_bin_sha256, paths in bin_paths.items():
                        bin_bin_path: str = paths[0]
                        binary_name = os.path.basename(bin_bin_path)
                        # TODO: 筛选类型只要这几种
                        if "." not in binary_name or '.so' in binary_name:
                            binary = Binary(
                                name=binary_name,
                                type='lib' if '.so' in binary_name else 'bin',
                                tpl_name=tpl_name,
                                rel_path=os.path.relpath(bin_bin_path, conan_libs_builder_output_dir),
                                file_size_kb=os.path.getsize(bin_bin_path) / 1024,  # size in KB
                                sha256=bin_bin_sha256
                            )
                            binaries.append(binary)
                    binary_dict[tpl_name] = binaries

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

                # ----- 过滤条件 -----
                # TODO: 筛选要包含的第三方库的数量，以及编译配置
                # test_suite 至少 3 个第三方库
                if rel_reused_lib_num < min_reused_lib_num:
                    continue  # Skip this test case if reused libraries are less than the minimum required

                # 跳过静态链接编译的
                if "-static" in compile_config.profile:
                    continue

                test_software.test_binary_suites.append(test_suite)

    # 过滤掉空的
    test_softwares = [ts for ts in test_software_dict.values() if ts.test_binary_suites]
    return test_softwares


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
    # main()
    benchmark_check()