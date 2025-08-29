import os

from environs import Env

from app.interface import AnalysisResult, Library, AnalysisData, TargetBinary
from evaluation.general_benchmarks.interface import EvaluationReport

env = Env()
env.read_env(".env")  # load .env file

import json


def convert_result():
    """
    将结果转换为指定格式并保存到output_json_path

    """

    raw_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_comparison/ToolsForComparision/OSSPolice/results/raw_result.json"
    converted_conan_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/osspolice/raw_result_converted.json"


    with open(raw_evluation_report_path, "r", encoding='utf-8') as f:
        old_results = json.load(f)

    converted_results = []
    smartBinary_status_statistic = {}
    smartBeat_status_statistic = {}
    for result in old_results:
        """
            {
        "binary_name": "libedlib.so.1.2.6",
        "sha256": "31ac05e3f29f11df4af796125c2a4139ad29015022df5abf61b19e88042549fc",
        "binary_path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases/edlib/1.2.7/edlib_1.2.7_arm_64-gcc-release-shared/full_deploy/host/edlib/1.2.7/Release/armv8/lib/libedlib.so.1.2.6",
        "libraries": [
            {
                "id": 172,
                "name": "gcc",
                "alias": null,
                "vendor": null,
                "homepage": null,
                "source_code_url": null,
                "candidate_source_code_urls": [],
                "description": null,
                "sources": [],
                "licenses": [],
                "confidence": null,
                "occurrence": null,
                "is_valid": true,
                "note": ""
            }
        ],
        "duration": 0.41254208399914205,
        "duration_with_db_estimate": 2.1125420839991422,
        "err_msg": null
    },
        """
        binary_name = result['binary_name']
        sha256 = result['sha256']
        binary_path = result['binary_path']

        converted_results.append(AnalysisResult(
            binary_name = binary_name,
            binary_sha256= sha256,
            binary_path = binary_path,
            detected_libraries = [
                Library(
                    name= lib['name'],
                ) for lib in result['libraries']
            ],
            analysis_data=AnalysisData(
                target_binary=TargetBinary(
                    binary_name=binary_name,
                    relative_path=binary_path,
                    hash_sha256=sha256,
                    file_size_kb=0,
                )
            ),
        ))


    report = EvaluationReport(
            evaluation_results = converted_results,

        )

    with open(converted_conan_evluation_report_path, "w", encoding='utf-8') as f:
        json.dump(report.customer_serialize(), f, indent=4, ensure_ascii=False)
    print(converted_conan_evluation_report_path)
    print(os.path.exists(converted_conan_evluation_report_path))

def cal_efficiency():
    raw_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_comparison/ToolsForComparision/OSSPolice/results/raw_result.json"

    with open(raw_evluation_report_path, "r", encoding='utf-8') as f:
        raw_results = json.load(f)

    durations = []
    for result in raw_results:
        duration = result['duration'] + 0.5 # 如果实现在数据库中会慢一点。
        durations.append(duration)

    avg_duration = sum(durations) / len(durations)
    print(f"avg duration: {avg_duration}")

# convert_result()
cal_efficiency()