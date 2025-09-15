import copy
import json
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

from app.interface import AnalysisResult, TargetBinary
from app.databases.postgres_new.crud import library_curd
from app.services.tpl_detection.feature_matching.feature_matching_detector import _is_cpp_function_name
from evaluation.general_benchmarks.database_checker import get_library_string_counts
from evaluation.general_benchmarks.interface import AnalysisResultCheck, Benchmark, TestCase


import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.ticker import PercentFormatter

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.ticker import PercentFormatter

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.ticker import PercentFormatter

def _plot_feature_matching_top_n_effectiveness_figure(
    effectiveness_dict,
    *,
    savepath=None,
    dpi=300,
    figsize=(7.5, 2.6)
):
    # 论文风基础样式
    plt.style.use('default')
    rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "axes.linewidth": 1.0,
        "xtick.major.width": 0.9,
        "ytick.major.width": 0.9,
        "xtick.minor.width": 0.8,
        "ytick.minor.width": 0.8,
    })

    # 数据
    top_n_values = sorted(int(k) for k in effectiveness_dict.keys())
    precision_values = [effectiveness_dict[str(k)]["precision"] for k in top_n_values]
    recall_values    = [effectiveness_dict[str(k)]["recall"]    for k in top_n_values]
    f1_values        = [effectiveness_dict[str(k)]["f1_score"]  for k in top_n_values]

    # 画布：用 constrained layout，自动为图外图例留白
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi, layout='constrained')

    # 线与标记
    series = [
        ("Precision", precision_values, "-",  "o"),
        ("Recall",    recall_values,    "--", "s"),
        ("F1 score",  f1_values,        "-.", "^"),
    ]
    for label, y, ls, mk in series:
        ax.plot(
            top_n_values, y,
            linewidth=2.0,
            linestyle=ls,
            marker=mk,
            markersize=4.2,
            markerfacecolor="white",
            markeredgewidth=1.0,
            label=label
        )

    # 坐标轴与刻度
    ax.set_xlabel("Top N Results")
    ax.set_ylabel("Performance (%)")
    ax.set_xlim(min(top_n_values), max(top_n_values))
    ax.set_ylim(0, 100)

    xmax = max(top_n_values)
    xticks = [1] + [t for t in range(5, xmax + 1, 5)]
    if xmax not in xticks:
        xticks.append(xmax)
    ax.set_xticks(xticks)

    ax.set_yticks(range(0, 101, 10))
    ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))

    ax.tick_params(direction="in", length=4.5, width=0.9)
    ax.tick_params(axis="both", which="minor", direction="in", length=2.5)
    ax.minorticks_on()

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # 只保留水平网格
    ax.grid(axis="y", which="major", linestyle="-", linewidth=0.6, alpha=0.22)
    ax.grid(axis="y", which="minor", linestyle=":", linewidth=0.5, alpha=0.15)

    # 图例放在图外右侧（不会遮数据）
    ax.legend(
        loc='center left',
        bbox_to_anchor=(1.02, 0.5),
        frameon=False
    )

    # 在 x=6 处画竖线并简短标注
    ax.axvline(x=6, color='gray', linestyle=':', linewidth=1.2)
    ax.text(6, 96, '', rotation=90, va='top', ha='right', fontsize=9, color='gray')

    # 保存或展示
    if savepath:
        fig.savefig(f"{savepath}.pdf", bbox_inches='tight')
        fig.savefig(f"{savepath}.png", bbox_inches='tight')
    else:
        plt.show()

    print("建议图题：Performance of the basic string matching tool with different Top N parameters")



def plot_feature_matching_top_n_effectiveness_figure(effectiveness_analysis_result_path):
    """
    绘制特征匹配效果分析图表
    :param effectiveness_analysis_result_path: 效果分析结果文件路径
    """
    # 加载效果分析结果
    with open(effectiveness_analysis_result_path, "r", encoding="utf-8") as f:
        effectiveness_dict = json.load(f)

    # 绘制图表
    _plot_feature_matching_top_n_effectiveness_figure(effectiveness_dict)


def analyze_feature_matching_top_n_effectiveness(evaluator,
                                                 evaluation_result_path,
                                                 top_n_effectiveness_analysis_result_path: str = None, top_n=10):
    """
    从大到小遍历，计算取不同的top_n的时候的effectiveness, 结果如何？
    """

    # 加载实验结果
    print(f"loading data")
    evaluation_results = _load_feature_matching_results(evaluation_result_path)

    # 统计分析
    top_n_effectiveness_dict = {}
    top_n_evaluation_results = copy.deepcopy(evaluation_results)
    for top_n in range(top_n, 0, -1):
        # 截取前top_n个检测结果
        for result in top_n_evaluation_results:
            result.detected_libraries = result.detected_libraries[:top_n]

        # 检查正确性
        result_check_lst = evaluator.check_result(top_n_evaluation_results)

        # 计算评估指标
        effectiveness = evaluator._cal_effectiveness(result_check_lst)

        # 预览评估指标
        print(top_n, effectiveness)

        # 记录评估指标
        top_n_effectiveness_dict[top_n] = effectiveness.customer_serialize()

    with open(top_n_effectiveness_analysis_result_path, "w", encoding="utf-8") as f:
        json.dump(top_n_effectiveness_dict, f, indent=4, ensure_ascii=False)


def _load_feature_matching_results(evaluation_result_path):
    """
    从评估结果文件中加载特征匹配检测结果
    :param evaluation_result_path: 评估结果文件路径
    :return: 特征匹配检测结果列表
    """
    with open(evaluation_result_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    evaluation_results = [AnalysisResult.init_from_dict(result) for result in data['evaluation_results']]
    return evaluation_results


def filter_strings_to_match(target_binary: TargetBinary) -> List[str]:
    strings_to_match = set()
    for s in target_binary.strings:
        if not (5 < len(s) < 500):
            continue

        # 排除掉符合函数名规则的字符串，不匹配函数名
        if _is_cpp_function_name(s):
            continue

        strings_to_match.add(s.strip())

    return list(strings_to_match)


from typing import List, Dict, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter


@dataclass
class TestCaseFailureStats:
    """测试用例级别的失败统计"""
    total_failed_test_cases: int = 0
    bin_failed_test_cases: int = 0
    so_failed_test_cases: int = 0

    # 按原因分类的测试用例数量
    db_not_recorded_cases: int = 0
    db_no_strings_cases: int = 0
    db_few_strings_cases: int = 0
    db_limited_strings_cases: int = 0
    binary_too_small_cases: int = 0
    binary_few_strings_cases: int = 0
    binary_limited_strings_cases: int = 0
    feature_mismatch_cases: int = 0
    unclassified_cases: int = 0


@dataclass
class LibraryFailureStats:
    """库级别的失败统计"""
    total_failed_libraries: int = 0

    # 按原因分类的库数量
    db_not_recorded_libs: int = 0
    db_no_strings_libs: int = 0
    db_few_strings_libs: int = 0
    db_limited_strings_libs: int = 0
    binary_too_small_libs: int = 0
    binary_few_strings_libs: int = 0
    binary_limited_strings_libs: int = 0
    feature_mismatch_libs: int = 0
    unclassified_libs: int = 0


@dataclass
class FailureReasonStats:
    """失败原因统计"""
    # 数据库相关原因
    not_recorded_libraries: List[str] = field(default_factory=list)
    recorded_no_strings: List[str] = field(default_factory=list)
    recorded_few_strings: List[str] = field(default_factory=list)  # < 10
    recorded_limited_strings: List[str] = field(default_factory=list)  # 10-50

    # 二进制文件相关原因
    binary_too_small: List[Tuple[str, str, float]] = field(default_factory=list)  # (lib_name, binary_hash, size_kb)
    binary_few_strings: List[Tuple[str, str]] = field(default_factory=list)  # (lib_name, binary_hash)
    binary_limited_strings: List[Tuple[str, str]] = field(default_factory=list)

    # 特征匹配相关原因
    feature_mismatch: List[Tuple[str, str]] = field(default_factory=list)  # 有足够特征但不匹配

    # 未分类的失败案例
    unclassified: List[Tuple[str, str]] = field(default_factory=list)

    # 文件类型统计 (只统计bin和so)
    bin_failures: int = 0
    so_failures: int = 0


@dataclass
class LibraryFailureInfo:
    """单个库的失败信息"""
    library_name: str
    total_test_cases: int
    failed_test_cases: int
    success_rate: float
    string_count: int
    failure_reason: str
    sample_binaries: List[str] = field(default_factory=list)  # 示例失败的二进制文件


@dataclass
class FailureAnalysisReport:
    """失败分析报告"""
    # 总体统计
    total_test_cases: int
    total_failed_cases: int
    failed_libraries_count: int
    unique_failed_libraries: Set[str]

    # 测试用例级别统计
    test_case_stats: TestCaseFailureStats

    # 库级别统计
    library_stats: LibraryFailureStats

    # 按原因分类的统计
    failure_stats: FailureReasonStats

    # 库级别的失败分析
    library_failures: List[LibraryFailureInfo]


def analyze_feature_matching_failures(evaluator,
                                      benchmark_path: str,
                                      evaluation_result_path: str,
                                      top_n: int = 3,
                                      few_strings_threshold: int = 10,
                                      limited_strings_threshold: int = 50,
                                      small_file_threshold_kb: float = 50.0) -> FailureAnalysisReport:
    """
    全面分析特征匹配失败的案例

    Args:
        evaluator: 评估器
        benchmark_path: 基准测试文件路径
        evaluation_result_path: 评估结果文件路径
        top_n: 考虑前n个检测结果
        few_strings_threshold: 少量字符串阈值
        limited_strings_threshold: 有限字符串阈值
        small_file_threshold_kb: 小文件大小阈值(KB)

    Returns:
        FailureAnalysisReport: 详细的失败分析报告
    """

    # 1. 加载数据
    benchmark = Benchmark.load_from_json_file(benchmark_path)
    tc_dict = {tc.test_binary.sha256: tc for tc in benchmark.test_cases}
    evaluation_results: List[AnalysisResult] = _load_feature_matching_results(evaluation_result_path)

    # 截取前top_n个检测结果
    for result in evaluation_results:
        result.detected_libraries = result.detected_libraries[:top_n]

    # 2. 检查正确性
    result_check_lst: List[AnalysisResultCheck] = evaluator.check_result(evaluation_results)

    # 3. 收集失败案例
    failed_cases = defaultdict(list)  # library_name -> [(tc, result, result_check)]
    total_failed_cases = 0

    for result, result_check in zip(evaluation_results, result_check_lst):
        if result_check.hs_fn:
            total_failed_cases += 1
            for tpl_name in result_check.fn_lib_names:
                tc = tc_dict.get(result.binary_sha256)
                failed_cases[tpl_name].append((tc, result, result_check))

    # 4. 统计每个库的测试用例数量
    library_case_count = defaultdict(int)
    for tc in benchmark.test_cases:
        for lib in tc.reused_libraries:
            library_case_count[lib.name] += 1

    # 5. 批量查询库的字符串数量
    library_names = list(failed_cases.keys())
    lib_string_counts = get_library_string_counts(library_names)  # 使用你之前的函数

    # 6. 分析失败原因
    failure_stats = FailureReasonStats()
    library_failures = []

    for lib_name, failed_tc_list in failed_cases.items():
        string_count = lib_string_counts.get(lib_name)
        total_cases = library_case_count[lib_name]
        failed_cases_count = len(failed_tc_list)
        success_rate = (total_cases - failed_cases_count) / total_cases * 100

        # 确定失败原因
        failure_reason = _classify_library_failure_reason(
            lib_name, string_count, failed_tc_list,
            few_strings_threshold, limited_strings_threshold,
            small_file_threshold_kb, failure_stats
        )

        # 收集示例二进制文件
        sample_binaries = [tc.test_binary.relative_path for tc, _, _ in failed_tc_list[:3]]

        library_failures.append(LibraryFailureInfo(
            library_name=lib_name,
            total_test_cases=total_cases,
            failed_test_cases=failed_cases_count,
            success_rate=success_rate,
            string_count=string_count if string_count is not None else -1,
            failure_reason=failure_reason,
            sample_binaries=sample_binaries
        ))

    # 7. 统计测试用例和库级别的失败情况
    test_case_stats = TestCaseFailureStats()
    library_stats = LibraryFailureStats()

    # 统计测试用例级别的失败原因
    for result, result_check in zip(evaluation_results, result_check_lst):
        if result_check.hs_fn:
            tc = tc_dict.get(result.binary_sha256)
            if tc:
                test_case_stats.total_failed_test_cases += 1

                # 统计文件类型
                if tc.test_binary.relative_path.endswith('.so'):
                    test_case_stats.so_failed_test_cases += 1
                else:
                    test_case_stats.bin_failed_test_cases += 1

                # 为每个失败的库分类测试用例
                for lib_name in result_check.fn_lib_names:
                    failure_reason = None
                    for lib_failure in library_failures:
                        if lib_failure.library_name == lib_name:
                            failure_reason = lib_failure.failure_reason
                            break

                    # 根据库的失败原因统计测试用例
                    if failure_reason == "数据库未收录":
                        test_case_stats.db_not_recorded_cases += 1
                    elif failure_reason == "已收录但无字符串":
                        test_case_stats.db_no_strings_cases += 1
                    elif failure_reason == "已收录但字符串很少":
                        test_case_stats.db_few_strings_cases += 1
                    elif failure_reason == "已收录但字符串有限":
                        test_case_stats.db_limited_strings_cases += 1
                    elif failure_reason == "二进制文件太小":
                        test_case_stats.binary_too_small_cases += 1
                    elif failure_reason == "二进制文件字符串很少":
                        test_case_stats.binary_few_strings_cases += 1
                    elif failure_reason == "二进制文件字符串有限":
                        test_case_stats.binary_limited_strings_cases += 1
                    elif failure_reason == "特征不匹配":
                        test_case_stats.feature_mismatch_cases += 1
                    else:
                        test_case_stats.unclassified_cases += 1

    # 统计库级别的失败情况
    library_stats.total_failed_libraries = len(library_failures)
    for lib_failure in library_failures:
        if lib_failure.failure_reason == "数据库未收录":
            library_stats.db_not_recorded_libs += 1
        elif lib_failure.failure_reason == "已收录但无字符串":
            library_stats.db_no_strings_libs += 1
        elif lib_failure.failure_reason == "已收录但字符串很少":
            library_stats.db_few_strings_libs += 1
        elif lib_failure.failure_reason == "已收录但字符串有限":
            library_stats.db_limited_strings_libs += 1
        elif lib_failure.failure_reason == "二进制文件太小":
            library_stats.binary_too_small_libs += 1
        elif lib_failure.failure_reason == "二进制文件字符串很少":
            library_stats.binary_few_strings_libs += 1
        elif lib_failure.failure_reason == "二进制文件字符串有限":
            library_stats.binary_limited_strings_libs += 1
        elif lib_failure.failure_reason == "特征不匹配":
            library_stats.feature_mismatch_libs += 1
        else:
            library_stats.unclassified_libs += 1

    # 8. 生成报告
    report = FailureAnalysisReport(
        total_test_cases=len(evaluation_results),
        total_failed_cases=total_failed_cases,
        failed_libraries_count=len(failed_cases),
        unique_failed_libraries=set(failed_cases.keys()),
        test_case_stats=test_case_stats,
        library_stats=library_stats,
        failure_stats=failure_stats,
        library_failures=sorted(library_failures, key=lambda x: x.failed_test_cases, reverse=True)
    )

    return report


def _classify_library_failure_reason(lib_name: str,
                                     string_count: int,
                                     failed_tc_list: List,
                                     few_threshold: int,
                                     limited_threshold: int,
                                     small_file_threshold_kb: float,
                                     failure_stats: FailureReasonStats) -> str:
    """分类库的失败原因"""

    if string_count is None:
        failure_stats.not_recorded_libraries.append(lib_name)
        return "数据库未收录"
    elif string_count == 0:
        failure_stats.recorded_no_strings.append(lib_name)
        return "已收录但无字符串"
    elif string_count < few_threshold:
        failure_stats.recorded_few_strings.append(lib_name)
        return "已收录但字符串很少"
    elif string_count < limited_threshold:
        failure_stats.recorded_limited_strings.append(lib_name)
        return "已收录但字符串有限"
    else:
        # 库有足够字符串，分析二进制文件
        return _analyze_binary_failure_reasons(lib_name, failed_tc_list,
                                               small_file_threshold_kb, failure_stats)


def _analyze_binary_failure_reasons(lib_name: str,
                                    failed_tc_list: List,
                                    small_file_threshold_kb: float,
                                    failure_stats: FailureReasonStats) -> str:
    """分析二进制文件相关的失败原因"""

    binary_string_counts = []
    small_file_count = 0

    for tc, result, result_check in failed_tc_list:
        try:
            binary_hash = tc.test_binary.sha256
            file_size_kb = tc.test_binary.file_size_kb

            # 统计文件类型 (只统计bin和so)
            if tc.test_binary.relative_path.endswith('.so'):
                failure_stats.so_failures += 1
            else:
                failure_stats.bin_failures += 1

            # 检查文件大小
            if file_size_kb < small_file_threshold_kb:
                small_file_count += 1
                failure_stats.binary_too_small.append((lib_name, binary_hash, file_size_kb))
                continue

            # 分析字符串数量
            target_binary = result.analysis_data.target_binary

            # 筛选前的字符串数量
            original_strings_count = len(target_binary.strings)

            # 筛选后的字符串数量
            strings_to_match = filter_strings_to_match(target_binary)
            filtered_strings_count = len(strings_to_match)

            # 不打印详细信息
            binary_string_counts.append(filtered_strings_count)

            if filtered_strings_count < 10:
                failure_stats.binary_few_strings.append((lib_name, binary_hash))
            elif filtered_strings_count < 50:
                failure_stats.binary_limited_strings.append((lib_name, binary_hash))
            else:
                failure_stats.feature_mismatch.append((lib_name, binary_hash))
        except:
            failure_stats.unclassified.append((lib_name, tc.test_binary.sha256))

    # 根据主要原因确定失败类型
    total_cases = len(failed_tc_list)

    if small_file_count > total_cases * 0.5:  # 超过一半是小文件
        return "二进制文件太小"
    elif binary_string_counts:
        avg_binary_strings = sum(binary_string_counts) / len(binary_string_counts)
        if avg_binary_strings < 10:
            return "二进制文件字符串很少"
        elif avg_binary_strings < 50:
            return "二进制文件字符串有限"
        else:
            return "特征不匹配"
    else:
        return "二进制文件太小"


def print_failure_analysis_report(report: FailureAnalysisReport):
    """打印失败分析报告"""

    print("\n" + "=" * 80)
    print("🔍 TPL Detection 失败案例分析报告")
    print("=" * 80)

    # 总体统计
    print(f"\n📊 总体统计:")
    print(f"   总测试用例数: {report.total_test_cases}")
    print(f"   失败测试用例数: {report.total_failed_cases}")
    print(f"   测试用例失败率: {report.total_failed_cases / report.total_test_cases * 100:.1f}%")
    print(f"   涉及失败的库数量: {report.failed_libraries_count}")

    # 测试用例级别的失败分析
    print(f"\n🎯 测试用例级别失败原因分布:")
    tc_stats = report.test_case_stats
    total_case_failures = tc_stats.total_failed_test_cases

    if total_case_failures > 0:
        print(
            f"   数据库未收录: {tc_stats.db_not_recorded_cases} 个测试用例 ({tc_stats.db_not_recorded_cases / total_case_failures * 100:.1f}%)")
        print(
            f"   已收录但无字符串: {tc_stats.db_no_strings_cases} 个测试用例 ({tc_stats.db_no_strings_cases / total_case_failures * 100:.1f}%)")
        print(
            f"   已收录但字符串很少: {tc_stats.db_few_strings_cases} 个测试用例 ({tc_stats.db_few_strings_cases / total_case_failures * 100:.1f}%)")
        print(
            f"   已收录但字符串有限: {tc_stats.db_limited_strings_cases} 个测试用例 ({tc_stats.db_limited_strings_cases / total_case_failures * 100:.1f}%)")
        print(
            f"   二进制文件太小: {tc_stats.binary_too_small_cases} 个测试用例 ({tc_stats.binary_too_small_cases / total_case_failures * 100:.1f}%)")
        print(
            f"   二进制文件字符串很少: {tc_stats.binary_few_strings_cases} 个测试用例 ({tc_stats.binary_few_strings_cases / total_case_failures * 100:.1f}%)")
        print(
            f"   二进制文件字符串有限: {tc_stats.binary_limited_strings_cases} 个测试用例 ({tc_stats.binary_limited_strings_cases / total_case_failures * 100:.1f}%)")
        print(
            f"   特征不匹配: {tc_stats.feature_mismatch_cases} 个测试用例 ({tc_stats.feature_mismatch_cases / total_case_failures * 100:.1f}%)")
        if tc_stats.unclassified_cases > 0:
            print(
                f"   未分类: {tc_stats.unclassified_cases} 个测试用例 ({tc_stats.unclassified_cases / total_case_failures * 100:.1f}%)")

    # 测试用例文件类型分布
    print(f"\n📁 失败测试用例文件类型分布:")
    total_failed_files = tc_stats.bin_failed_test_cases + tc_stats.so_failed_test_cases
    if total_failed_files > 0:
        print(
            f"   bin文件: {tc_stats.bin_failed_test_cases} 个测试用例 ({tc_stats.bin_failed_test_cases / total_failed_files * 100:.1f}%)")
        print(
            f"   so文件: {tc_stats.so_failed_test_cases} 个测试用例 ({tc_stats.so_failed_test_cases / total_failed_files * 100:.1f}%)")

    # 库级别的失败分析
    print(f"\n📚 库级别失败原因分布:")
    lib_stats = report.library_stats
    total_lib_failures = lib_stats.total_failed_libraries

    if total_lib_failures > 0:
        print(
            f"   数据库未收录: {lib_stats.db_not_recorded_libs} 个库 ({lib_stats.db_not_recorded_libs / total_lib_failures * 100:.1f}%)")
        print(
            f"   已收录但无字符串: {lib_stats.db_no_strings_libs} 个库 ({lib_stats.db_no_strings_libs / total_lib_failures * 100:.1f}%)")
        print(
            f"   已收录但字符串很少: {lib_stats.db_few_strings_libs} 个库 ({lib_stats.db_few_strings_libs / total_lib_failures * 100:.1f}%)")
        print(
            f"   已收录但字符串有限: {lib_stats.db_limited_strings_libs} 个库 ({lib_stats.db_limited_strings_libs / total_lib_failures * 100:.1f}%)")
        print(
            f"   二进制文件太小: {lib_stats.binary_too_small_libs} 个库 ({lib_stats.binary_too_small_libs / total_lib_failures * 100:.1f}%)")
        print(
            f"   二进制文件字符串很少: {lib_stats.binary_few_strings_libs} 个库 ({lib_stats.binary_few_strings_libs / total_lib_failures * 100:.1f}%)")
        print(
            f"   二进制文件字符串有限: {lib_stats.binary_limited_strings_libs} 个库 ({lib_stats.binary_limited_strings_libs / total_lib_failures * 100:.1f}%)")
        print(
            f"   特征不匹配: {lib_stats.feature_mismatch_libs} 个库 ({lib_stats.feature_mismatch_libs / total_lib_failures * 100:.1f}%)")
        if lib_stats.unclassified_libs > 0:
            print(
                f"   未分类: {lib_stats.unclassified_libs} 个库 ({lib_stats.unclassified_libs / total_lib_failures * 100:.1f}%)")

    # 详细的库失败分析（前20个）
    print(f"\n📋 库级别失败详情 (按失败测试用例数排序，前20个):")
    print(f"{'序号':<4} {'库名':<25} {'失败/总数':<12} {'成功率':<8} {'字符串数':<10} {'失败原因':<15}")
    print("-" * 80)

    for i, lib_failure in enumerate(report.library_failures[:20], 1):
        string_count_str = str(lib_failure.string_count) if lib_failure.string_count >= 0 else "未收录"
        print(f"{i:<4} {lib_failure.library_name:<25} "
              f"{lib_failure.failed_test_cases}/{lib_failure.total_test_cases:<11} "
              f"{lib_failure.success_rate:<7.1f}% {string_count_str:<10} "
              f"{lib_failure.failure_reason}")

    if len(report.library_failures) > 20:
        print(f"   ... 还有 {len(report.library_failures) - 20} 个库")

    print("\n" + "=" * 80)


# 使用示例
def run_failure_analysis(evaluator, benchmark_path, evaluation_result_path,
                         top_n=3, small_file_threshold_kb=50.0):
    """运行失败分析"""

    # 执行分析
    report = analyze_feature_matching_failures(
        evaluator=evaluator,
        benchmark_path=benchmark_path,
        evaluation_result_path=evaluation_result_path,
        top_n=top_n,
        small_file_threshold_kb=small_file_threshold_kb
    )

    # 打印报告
    print_failure_analysis_report(report)

    # 返回报告供进一步分析
    return report

