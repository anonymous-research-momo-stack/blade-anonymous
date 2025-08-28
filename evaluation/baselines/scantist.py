import os
import csv
import json
from pathlib import Path

from environs import Env

from app.interface import AnalysisResult, Library, AnalysisData, TargetBinary

from evaluation.general_benchmarks.interface import Benchmark
from evaluation.general_benchmarks.interface import EvaluationReport

env = Env()
env.read_env(".env")  # load .env file


def convert_csv_result():
    """
    将CSV格式的SCA扫描结果转换为指定格式并保存到output_json_path
    """
    Conan_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark_20250806_1524.json"

    benchmark = Benchmark.load_from_json_file(Conan_benchmark_meta)

    relative_path_to_hash = {}
    for tc in benchmark.test_cases:
        relative_path_to_hash[tc.test_binary.relative_path] = tc.test_binary.sha256

    # 输入CSV文件路径
    raw_csv_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/scantist/291-75403-xd70-无agent-扫描报告-2025-08-06T09_36_22+08_00/75403-组件.csv"

    # 输出JSON文件路径
    converted_json_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/scantist/291-75403-xd70-无agent-扫描报告-2025-08-06T09_36_22+08_00/result_converted.json"

    converted_results = []

    # 读取CSV文件
    with open(raw_csv_report_path, "r", encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)

        for row in csv_reader:
            # 获取组件信息
            component_name = row.get('组件名', '')
            version = row.get('版本号', '')
            file_paths = row.get('文件路径', '')

            # 解析文件路径（多个路径用逗号分隔）
            libraries = []
            if file_paths:
                # 分割路径并清理空白字符
                paths = [path.strip() for path in file_paths.split(',') if path.strip()]

                # 为每个路径创建一个AnalysisResult
                for file_path in paths:
                    # 从路径中提取二进制文件名
                    binary_name = Path(file_path).name if file_path else ''

                    relative_path = file_path[38:]
                    sha256 = relative_path_to_hash[relative_path]
                    # 创建Library对象
                    library = Library(
                        name=component_name,
                        version=version
                    )
                    libraries.append(library)

        # 创建AnalysisResult对象
        analysis_result = AnalysisResult(
            binary_name=binary_name,
            binary_sha256=sha256,  # CSV中没有，填空字符串
            binary_path=file_path,
            detected_libraries=libraries,
            analysis_data=AnalysisData(
                target_binary=TargetBinary(
                    binary_name=binary_name,
                    relative_path=relative_path,
                    hash_sha256=sha256,  # CSV中没有，填空字符串
                    file_size_kb=0,  # CSV中没有，填0
                )
            ),
        )

        converted_results.append(analysis_result)

    print(f"总共转换了 {len(converted_results)} 个分析结果")

    # 创建评估报告
    report = EvaluationReport(
        evaluation_results=converted_results,
    )

    # 保存到JSON文件
    with open(converted_json_report_path, "w", encoding='utf-8') as f:
        json.dump(report.customer_serialize(), f, indent=4, ensure_ascii=False)

    print(f"结果已保存到: {converted_json_report_path}")
    print(f"文件是否存在: {os.path.exists(converted_json_report_path)}")


if __name__ == "__main__":
    convert_csv_result()