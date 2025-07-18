#!/usr/bin/env python3
"""
Conan 2.x 库编译脚本
功能：自动下载、编译指定的C++库，并输出二进制文件和完整的依赖元信息
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

from loguru import logger
logger.remove()
logger.add(sys.stderr, level="INFO")

class ConanBuildError(Exception):
    """Conan编译相关错误"""
    pass


class ConanLibraryBuilder:
    """Conan库编译器"""

    def __init__(self):
        self.temp_dir = None
        self.conan_version = None

    def __enter__(self):
        """进入上下文管理器，创建临时目录"""
        self.temp_dir = tempfile.mkdtemp(prefix='conan_build_')
        logger.info(f"创建临时工作目录: {self.temp_dir}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器，清理临时目录"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"清理临时目录: {self.temp_dir}")

    def _run_command(self, cmd: List[str], capture_output: bool = True,
                     check: bool = True) -> subprocess.CompletedProcess:
        """执行命令"""
        logger.debug(f"执行命令: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=check,
                cwd=self.temp_dir
            )
            if result.stdout:
                logger.debug(f"命令输出: {result.stdout}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"命令执行失败: {e}")
            logger.error(f"错误输出: {e.stderr}")
            raise ConanBuildError(f"命令执行失败: {' '.join(cmd)}\\n{e.stderr}")

    def _check_conan_available(self) -> str:
        """检查Conan是否可用并获取版本"""
        try:
            result = self._run_command(['conan', '--version'])
            version_line = result.stdout.strip()
            logger.info(f"检测到Conan版本: {version_line}")

            # 检查是否为Conan 2.x
            if not version_line.startswith('Conan version 2.'):
                raise ConanBuildError(f"需要Conan 2.x版本，当前版本: {version_line}")

            self.conan_version = version_line
            return version_line
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ConanBuildError("未找到Conan命令，请确保已安装Conan 2.x")

    def _create_conanfile_txt(self, library_name: str, version: str) -> str:
        """创建临时的conanfile.txt"""
        conanfile_content = f"""[requires]
{library_name}/{version}

[generators]
CMakeDeps
CMakeToolchain
"""
        conanfile_path = os.path.join(self.temp_dir, 'conanfile.txt')
        with open(conanfile_path, 'w') as f:
            f.write(conanfile_content)
        logger.debug(f"创建conanfile.txt: {conanfile_path}")
        return conanfile_path

    def _get_library_info(self, library_name: str, version: str) -> Dict[str, Any]:
        """获取库的基本信息"""
        logger.info(f"获取库信息: {library_name}/{version}")

        # 创建临时目录专门用于获取库信息，避免与主工作目录的conanfile.txt冲突
        info_temp_dir = tempfile.mkdtemp(prefix='conan_info_')

        try:
            # 创建临时conanfile.py来获取库信息
            conanfile_py = f"""from conan import ConanFile

class TempConan(ConanFile):
    requires = "{library_name}/{version}"
"""
            conanfile_path = os.path.join(info_temp_dir, 'conanfile.py')
            with open(conanfile_path, 'w') as f:
                f.write(conanfile_py)

            # 使用conan graph info获取信息
            cmd = [
                'conan', 'graph', 'info', info_temp_dir,
                '--format=json',
                '-r=conancenter'
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            graph_data = json.loads(result.stdout)

            # 从图数据中提取目标库信息
            target_node = None
            for node_id, node in graph_data.get('graph', {}).get('nodes', {}).items():
                if node.get('name') == library_name and node.get('version') == version:
                    target_node = node
                    break

            if not target_node:
                raise ConanBuildError(f"未找到库 {library_name}/{version}")

            return {
                'name': target_node.get('name', library_name),
                'version': target_node.get('version', version),
                'description': target_node.get('description', ''),
                'license': target_node.get('license', ''),
                'homepage': target_node.get('homepage', ''),
                'url': target_node.get('url', ''),
                'topics': target_node.get('topics', [])
            }

        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"无法解析库信息: {e}")
            return {
                'name': library_name,
                'version': version,
                'description': '',
                'license': '',
                'homepage': '',
                'url': '',
                'topics': []
            }
        finally:
            # 清理临时目录
            if os.path.exists(info_temp_dir):
                shutil.rmtree(info_temp_dir)

    def _get_dependency_graph(self, library_name: str, version: str,
                              settings: Dict[str, str], options: Dict[str, Any]) -> Dict[str, Any]:
        """获取依赖图谱"""
        logger.info(f"分析依赖图谱: {library_name}/{version}")

        # 构建conan graph info命令
        cmd = [
            'conan', 'graph', 'info', '.',
            '--format=json',
            '-r=conancenter'
        ]

        # 添加settings参数
        for key, value in settings.items():
            cmd.extend(['-s', f'{key}={value}'])

        # 添加options参数
        for key, value in options.items():
            if key.startswith(library_name):
                cmd.extend(['-o', f'{key}={value}'])
            else:
                cmd.extend(['-o', f'{library_name}/*:{key}={value}'])

        try:
            result = self._run_command(cmd)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.error(f"获取依赖图谱失败: {e}")
            raise ConanBuildError(f"无法获取依赖图谱: {e}")

    def _parse_dependency_tree(self, graph_data: Dict[str, Any],
                               target_lib: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """解析依赖图谱，生成树状和扁平结构"""
        nodes = graph_data.get('graph', {}).get('nodes', {})

        # 查找目标库节点
        target_node_id = None
        for node_id, node in nodes.items():
            if node.get('name') == target_lib and node.get('recipe') != 'Cli':
                target_node_id = node_id
                break

        if not target_node_id:
            raise ConanBuildError(f"未找到目标库 {target_lib}")

        # 构建邻接表
        adjacency = {}
        for node_id in nodes:
            adjacency[node_id] = []

        # 从requires字段构建依赖关系
        for node_id, node in nodes.items():
            requires = node.get('requires', [])
            for req in requires:
                if isinstance(req, str):
                    # 查找对应的节点ID
                    for req_node_id, req_node in nodes.items():
                        req_name = req.split('/')[0] if '/' in req else req
                        if req_node.get('name') == req_name:
                            adjacency[node_id].append(req_node_id)
                            break

        # 生成依赖树
        def build_tree(node_id: str, level: int = 0, visited: set = None) -> Dict[str, Any]:
            if visited is None:
                visited = set()

            node = nodes[node_id]
            name = node.get('name')
            version = node.get('version')

            if not name or not version:
                return None

            # 获取链接类型
            shared_option = node.get('options', {}).get('shared', False)
            link_type = 'shared' if shared_option else 'static'

            tree_node = {
                'name': name,
                'version': version,
                'link_type': link_type,
                'level': level,
                'node_id': node_id,
                'direct_dependencies': [],
                'children': []
            }

            # 如果已访问过（钻石依赖），标记引用
            if node_id in visited:
                tree_node['reference_to'] = node_id
                tree_node['note'] = 'shared_dependency'
                return tree_node

            visited.add(node_id)

            # 递归构建子节点
            for child_id in adjacency.get(node_id, []):
                child_node = nodes.get(child_id)
                if child_node and child_node.get('name'):
                    tree_node['direct_dependencies'].append(child_node.get('name'))
                    child_tree = build_tree(child_id, level + 1, visited.copy())
                    if child_tree:
                        tree_node['children'].append(child_tree)

            return tree_node

        # 生成扁平列表
        def build_flat_list() -> List[Dict[str, Any]]:
            flat_deps = {}

            def traverse(node_id: str, level: int, path: List[str]):
                node = nodes.get(node_id)
                if not node or not node.get('name'):
                    return

                name = node.get('name')
                version = node.get('version')
                key = f"{name}/{version}"

                shared_option = node.get('options', {}).get('shared', False)
                link_type = 'shared' if shared_option else 'static'

                if key not in flat_deps:
                    flat_deps[key] = {
                        'name': name,
                        'version': version,
                        'link_type': link_type,
                        'min_level': level,
                        'used_by': set(),
                        'node_id': node_id,
                        'paths': []
                    }
                else:
                    flat_deps[key]['min_level'] = min(flat_deps[key]['min_level'], level)

                # 添加使用路径
                if len(path) > 0:
                    flat_deps[key]['used_by'].add(path[-1])
                else:
                    flat_deps[key]['used_by'].add('root')

                flat_deps[key]['paths'].append(' -> '.join(path + [name]))

                # 递归处理依赖
                for child_id in adjacency.get(node_id, []):
                    traverse(child_id, level + 1, path + [name])

            traverse(target_node_id, 0, [])

            # 转换为列表格式
            result = []
            for dep in flat_deps.values():
                dep['used_by'] = list(dep['used_by'])
                result.append(dep)

            return result

        tree = build_tree(target_node_id)
        flat_list = build_flat_list()

        # 检测钻石依赖
        diamond_deps = []
        for dep in flat_list:
            if len(dep['paths']) > 1:
                diamond_deps.append({
                    'package': f"{dep['name']}/{dep['version']}",
                    'paths': dep['paths']
                })

        # 生成摘要
        summary = {
            'total_packages': len(flat_list),
            'direct_dependencies': len([d for d in flat_list if d['min_level'] == 1]),
            'max_depth': max([d['min_level'] for d in flat_list]) if flat_list else 0,
            'shared_libraries': [d['name'] for d in flat_list if d['link_type'] == 'shared'],
            'static_libraries': [d['name'] for d in flat_list if d['link_type'] == 'static'],
            'diamond_dependencies': diamond_deps
        }

        return {
            'structure': 'tree',
            'dependencies': [tree] if tree else []
        }, {
            'structure': 'flat',
            'unique_dependencies': flat_list
        }, summary

    def _install_library(self, library_name: str, version: str,
                         settings: Dict[str, str], options: Dict[str, Any],
                         output_dir: str) -> str:
        """使用conan install安装库并部署到目标目录"""
        logger.info(f"开始安装库: {library_name}/{version}")

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 构建conan install命令
        cmd = [
            'conan', 'install', '.',
            '--build=missing',
            '--deployer=full_deploy',
            f'--deployer-folder={output_dir}',
            '-r=conancenter'
        ]

        # 添加settings
        for key, value in settings.items():
            cmd.extend(['-s', f'{key}={value}'])

        # 添加options
        for key, value in options.items():
            if key.startswith(library_name):
                cmd.extend(['-o', f'{key}={value}'])
            else:
                cmd.extend(['-o', f'{library_name}/*:{key}={value}'])

        try:
            print("Command: ", " ".join(cmd))
            result = self._run_command(cmd, capture_output=False)
            logger.info("库安装和部署完成")
            return output_dir
        except Exception as e:
            raise ConanBuildError(f"安装库失败: {e}")

    def _verify_deployment(self, output_dir: str):
        """验证部署是否成功"""
        if not os.path.exists(output_dir):
            logger.error(f"部署目录不存在: {output_dir}")
            return False

        # 简单统计
        file_count = sum(len(files) for _, _, files in os.walk(output_dir))
        if file_count == 0:
            logger.error("警告：没有文件被部署")
            return False
        else:
            logger.info(f"部署成功，共 {file_count} 个文件")
            return True

    def _generate_metadata(self, library_info: Dict[str, Any],
                           settings: Dict[str, str], options: Dict[str, Any],
                           dependency_tree: Dict[str, Any],
                           dependency_list: Dict[str, Any],
                           dependency_summary: Dict[str, Any],
                           build_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成元信息JSON"""

        metadata = {
            'target_library': library_info,
            'build_configuration': {
                'settings': settings,
                'options': options
            },
            'dependency_tree': dependency_tree,
            'dependency_list': dependency_list,
            'dependency_summary': dependency_summary,
            'build_info': {
                'timestamp': datetime.now().isoformat() + 'Z',
                'conan_version': self.conan_version,
                'build_from_source': build_info.get('build_from_source', []),
                'prebuilt_binaries': build_info.get('prebuilt_binaries', []),
                'diamond_dependency_resolution': 'conan_resolved'
            }
        }

        return metadata

    def build_library(self, library_name: str, version: str,
                      settings: Dict[str, str], options: Dict[str, Any],
                      output_dir: str) -> Dict[str, Any]:
        """主要的构建方法"""

        # 检查Conan
        self._check_conan_available()

        # 创建conanfile.txt
        self._create_conanfile_txt(library_name, version)

        # 获取库信息
        library_info = self._get_library_info(library_name, version)

        # 获取依赖图谱
        graph_data = self._get_dependency_graph(library_name, version, settings, options)

        # 解析依赖图谱
        dependency_tree, dependency_list, dependency_summary = self._parse_dependency_tree(
            graph_data, library_name
        )

        # 安装库并部署到目标目录
        self._install_library(library_name, version, settings, options, output_dir)

        # 验证部署结果
        if not self._verify_deployment(output_dir):
            raise ConanBuildError("部署验证失败")

        # 构建信息（这里可以添加更多逻辑来检测哪些包是从源码构建的）
        build_info = {
            'build_from_source': [library_name],  # 简化处理
            'prebuilt_binaries': [dep['name'] for dep in dependency_list['unique_dependencies']
                                  if dep['name'] != library_name]
        }

        # 生成元信息
        metadata = self._generate_metadata(
            library_info, settings, options,
            dependency_tree, dependency_list, dependency_summary,
            build_info
        )

        # 保存元信息文件
        metadata_path = os.path.join(output_dir, 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"元信息已保存到: {metadata_path}")

        return metadata


def build_custom_library(library_name: str, version: str, output_dir: str,
                         arch: str = 'x86_64', compiler: str = 'gcc',
                         compiler_version: str = '11', build_type: str = 'Release',
                         shared: bool = False, extra_settings: Dict[str, str] = None,
                         extra_options: Dict[str, Any] = None, verbose: bool = False) -> Dict[str, Any]:
    """
    便捷的库编译函数

    Args:
        library_name: 库名称
        version: 库版本
        output_dir: 输出目录
        arch: 架构 (默认: x86_64)
        compiler: 编译器 (默认: gcc)
        compiler_version: 编译器版本 (默认: 11)
        build_type: 构建类型 (默认: Release)
        shared: 是否构建共享库 (默认: False)
        extra_settings: 额外设置
        extra_options: 额外选项
        verbose: 详细输出 (默认: False)

    Returns:
        Dict[str, Any]: 包含完整元信息的字典

    Raises:
        ConanBuildError: 编译失败时抛出
    """

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    # 构建设置字典
    settings = {
        'arch': arch,
        'compiler': compiler,
        'compiler.version': compiler_version,
        'build_type': build_type
    }

    # 添加额外设置
    if extra_settings:
        settings.update(extra_settings)

    # 构建选项字典
    options = {'shared': shared}

    # 添加额外选项
    if extra_options:
        options.update(extra_options)

    with ConanLibraryBuilder() as builder:
        return builder.build_library(
            library_name=library_name,
            version=version,
            settings=settings,
            options=options,
            output_dir=output_dir
        )

def get_mac_variant_configs():
    # 根据你的实际环境：apple-clang 17.0, armv8架构
    mac_base_config = {
        'arch': 'armv8',
        'compiler': 'apple-clang',
        'compiler_version': '17',  # 修正：从15改为17
        'build_type': 'Release',
        'shared': True,
        'compiler.libcxx': 'libc++',
        'compiler.cppstd': 'gnu17'  # 与系统检测一致
    }

    # 变体配置，移除可能有问题的GCC配置
    variants = [
        ('baseline', mac_base_config),
        ('x86_64', {**mac_base_config, 'arch': 'x86_64'}),
        ('debug', {**mac_base_config, 'build_type': 'Debug'}),
        ('static', {**mac_base_config, 'shared': False}),
        # 注释掉GCC配置，因为在Apple Silicon Mac上可能需要额外配置
        # ('gcc', {**mac_base_config, 'compiler': 'gcc', 'compiler_version': '11'}),
    ]

    return variants

def get_ubuntu_variant_configs():
    """
    在Ubuntu 22.04上构建主要数据集：

    编译器变体：GCC 9/11/12/13, Clang 13/14/15/16
    构建类型：Release/Debug/RelWithDebInfo
    链接方式：Static/Shared
    优化级别：O0/O1/O2/O3/Os


    :return:
    """
    # ubuntu 24.04
    ubuntu_base_config = {
        'arch': 'x86_64',  # Ubuntu通常是x86_64架构
        'compiler': 'gcc',  # Ubuntu默认GCC编译器
        'compiler_version': '13',  # Ubuntu 24.04默认GCC版本
        'build_type': 'Release',
        'shared': True,
        'compiler.libcxx': 'libstdc++11',  # GNU C++标准库
        'compiler.cppstd': '17'  # 现代C++标准
    }

    # 变体配置, 目的是控制变量测试:架构,编译器,编译优化等级,动静态链接的影响
    variants = [
        ('baseline', ubuntu_base_config),
        ('armv8', {**ubuntu_base_config, 'arch': 'armv8'}),
        ('debug', {**ubuntu_base_config, 'build_type': 'Debug'}),
        ('static', {**ubuntu_base_config, 'shared': False}),
        ('clang', {**ubuntu_base_config, 'compiler': 'clang', 'compiler_version': '18'}),
    ]

    return variants

def build_comparison_configs(library_name: str, version: str, base_output_dir: str):
    """编译对比配置"""

    variants = get_mac_variant_configs()
    results = {}
    for variant_name, config in variants:
        print(f"编译配置: {variant_name}")

        # 构建输出目录
        output_dir = f"{base_output_dir}/{library_name}_{version}_{variant_name}"

        # 分离settings和options
        settings = {k: v for k, v in config.items() if k != 'shared'}
        options = {'shared': config['shared']}

        try:
            metadata = build_custom_library(
                library_name=library_name,
                version=version,
                output_dir=output_dir,
                arch=settings['arch'],
                compiler=settings['compiler'],
                compiler_version=settings['compiler_version'],
                build_type=settings['build_type'],
                shared=options['shared'],
                verbose=True
            )

            results[variant_name] = {
                'status': 'success',
                'config': config,
                'output_dir': output_dir,
                'metadata': metadata
            }
            print(f"✅ {variant_name} 编译成功")

        except Exception as e:
            results[variant_name] = {
                'status': 'failed',
                'config': config,
                'error': str(e)
            }
            print(f"❌ {variant_name} 编译失败: {e}")

    return results


def build_all_libraries(conan_libs_json_path:str,
                        output_dir:str = './benchmark_data'):
    with open(conan_libs_json_path, 'r', encoding='utf-8') as f:
        conan_lib_vers_dict = json.load(f)

    target_conan_lib_ver_dict = {lib_name: [lib_vers[0], lib_vers[-1]]
                                 for lib_name, lib_vers in conan_lib_vers_dict.items()}

    for lib, vers in list(target_conan_lib_ver_dict.items())[:3]:
        for ver in vers:
            base_output_dir = f'{output_dir}/{lib}/{ver}'
            os.makedirs(base_output_dir, exist_ok=True)
            build_comparison_configs(lib, ver, base_output_dir)



def demo():
    benchmark_output_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/benchmark_data"
    try:
        # 编译OpenSSL库的配置示例
        metadata = build_custom_library(
            # 基本库信息
            library_name='openssl',  # 指定要编译的库名称
            version='3.1.1',  # 指定库的版本号（修正为稳定版本）
            output_dir=f'{benchmark_output_dir}/openssl',  # 编译产物输出目录（修正路径）

            # 编译器配置
            compiler='clang',  # 使用clang编译器（而非默认的gcc）
            compiler_version='14',  # 指定clang编译器版本为14
            build_type='Debug',  # 构建Debug版本（包含调试信息，未优化）
            shared=False,  # 构建静态库（.a文件），而非动态库（.so文件）

            # 高级编译设置
            extra_settings={
                'compiler.libcxx': 'libc++',  # 使用libc++标准库（clang的默认C++标准库）
                'compiler.cppstd': '17'  # 指定C++17标准
            },

            # 库特定选项（移除可能不支持的选项）
            extra_options={
                # 移除可能不存在的选项，避免编译错误
            },

            # 输出控制
            verbose=True  # 启用详细日志输出，便于调试和监控编译过程
        )

        print(f"\n✅ OpenSSL库编译完成!")  # 修正打印信息
        print(f"依赖数量: {metadata['dependency_summary']['total_packages']}")

    except ConanBuildError as e:
        print(f"❌ 编译失败: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")


def batch_demo():
    benchmark_output_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/benchmark_data"
    try:
        # 编译OpenSSL库的多种配置
        results = build_comparison_configs(
            library_name='openssl',
            version='3.1.1',
            base_output_dir=f'{benchmark_output_dir}/openssl',
        )

        print(f"\n✅ OpenSSL库批量编译完成!")

        # 统计编译结果
        successful_builds = [name for name, result in results.items() if result['status'] == 'success']
        failed_builds = [name for name, result in results.items() if result['status'] == 'failed']

        print(f"成功编译: {len(successful_builds)} 个配置")
        print(f"失败编译: {len(failed_builds)} 个配置")

        # 显示每个成功配置的依赖信息
        for variant_name, result in results.items():
            if result['status'] == 'success':
                metadata = result['metadata']
                deps_count = metadata['dependency_summary']['total_packages']
                print(f"  {variant_name}: {deps_count} 个依赖包")
            else:
                print(f"  {variant_name}: 编译失败 - {result['error']}")

    except ConanBuildError as e:
        print(f"❌ 编译失败: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # demo()
    batch_demo()
    # conan_libs_json_path = '/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/benchmark_meta/conan_libs.json'
    # output_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/benchmark_data"
    # build_all_libraries(conan_libs_json_path, output_dir)