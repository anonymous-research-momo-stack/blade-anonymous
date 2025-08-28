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

    relative_hash_to_path = {}
    for tc in benchmark.test_cases:
        relative_hash_to_path[tc.test_binary.sha256] = tc.test_binary.relative_path

    # 输入CSV文件路径
    raw_csv_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/blackduck/test_cases.zip-components.csv"

    # 输出JSON文件路径
    converted_json_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/blackduck/result_converted.json"

    converted_results = []

    # 读取CSV文件
    with open(raw_csv_report_path, "r", encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)

        result_dict = {}
        for row in csv_reader:
            # 获取组件信息
            component_name = row.get('Component', '')
            version = row.get('Version', '')
            sha256 = row.get('Object', '')

            relative_path = relative_hash_to_path.get(sha256, '')
            # 从路径中提取二进制文件名
            binary_name = Path(relative_path).name if relative_path else ''

            # 创建Library对象
            library = Library(
                name=component_name,
                version=version
            )
            if sha256 not in result_dict:
                result_dict[sha256] = {
                    "binary_name": binary_name,
                    "binary_sha256": sha256,
                    "binary_path": relative_path,
                    "detected_libraries": [],
                }
            result_dict[sha256]["detected_libraries"].append(library)

        for sha256, info in result_dict.items():
            binary_name = info["binary_name"]
            relative_path = info["binary_path"]
            libraries = info["detected_libraries"]

            # 创建AnalysisResult对象
            analysis_result = AnalysisResult(
                binary_name=binary_name,
                binary_sha256=sha256,  # CSV中没有，填空字符串
                binary_path=relative_path,
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