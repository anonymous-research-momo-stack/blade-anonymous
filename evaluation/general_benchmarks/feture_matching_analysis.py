import copy
import json
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

from app.interface import AnalysisResult, TargetBinary
from app.databases.postgres_new.crud import library_curd
from app.services.tpl_detection.feature_matching.feature_matching_detector import _is_cpp_function_name
from evaluation.general_benchmarks.interface import AnalysisResultCheck, Benchmark, TestCase


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


def classify_feature_matching_cases_having_fn(evaluator,
                                              benchmark_path,
                                              evaluation_result_path,
                                              failed_cases_save_path: str = None,
                                              top_n=3):
    """
    漏报的案例的原因是什么？
        1. 数据原因？
            1. 没收录？或者收录错了？
            2. 没特征？
            3. 有特征，但是太少了？

        2. 测试用例原因
            1. 没有特征？
            2. 其他原因？

    :param evaluation_result_path:
    :param failed_cases_save_path:
    :return:
    """

    print(f"loading benchmark")
    benchmark = Benchmark.load_from_json_file(benchmark_path)
    tc_dict = {tc.test_binary.sha256: tc for tc in benchmark.test_cases}
    print(f"loading evaluation results")
    evaluation_results: List[AnalysisResult] = _load_feature_matching_results(evaluation_result_path)

    # 截取前top_n个检测结果
    for result in evaluation_results:
        result.detected_libraries = result.detected_libraries[:top_n]

    # 检查正确性
    result_check_lst: List[AnalysisResultCheck] = evaluator.check_result(evaluation_results)

    # ======= RQ 1 测试用例的漏报情况统计 ========
    failed_cases = {}
    for result, result_check in zip(evaluation_results, result_check_lst):
        if result_check.hs_fn:
            for tpl_name in result_check.fn_lib_names:
                if tpl_name not in failed_cases:
                    failed_cases[tpl_name] = []
                tc = tc_dict.get(result.binary_sha256)
                failed_cases[tpl_name].append((tc, result, result_check))
    print(f'----- test cases -----')
    print(f"tocal cases: {len(evaluation_results)}, has_fn_cases: {sum(len(failed_cases[tpl]) for tpl in failed_cases)}")

    # ======= RQ 2 库的漏报情况统计 ========
    # 先计算每个库有多少个测试用例
    library_case_count = {}
    for tc in benchmark.test_cases:
        for lib in tc.reused_libraries:
            lib_name = lib.name
            if lib_name not in library_case_count:
                library_case_count[lib_name] = 0
            library_case_count[lib_name] += 1

    # 然后计算每个库漏报的测试用例数量
    all_failed_count = 0
    partial_failed_count = 0
    for lib, failed_tc_lst in failed_cases.items():
        if len(failed_tc_lst) == library_case_count[lib]:
            all_failed_count += 1
        else:
            partial_failed_count += 1
    print(f'----- libraries -----')
    print(f"total failed libraries: {len(failed_cases)}, "
          f"all failed library count: {all_failed_count}, partial failed library count: {partial_failed_count}")

    # ======= RQ 3 失败的原因分类 ========
    """
        1. 数据原因？
            1. 没收录？或者收录错了？
            2. 没特征？
            3. 有特征，但是太少了？

        2. 测试用例原因
            1. 文件很小且没有特征？
            
            2. 其他原因？
    """
    not_recorded_libraries = []
    recorded_but_no_str_libraries = []
    recorded_but_less_str_libraries = []

    tc_with_strings_to_match_lt_10 = []
    tc_with_strings_to_match_lt_25 = []
    tc_with_strings_to_match_lt_50 = []

    unclassified_test_cases = []
    lib_str_count_dict = {}
    for lib_name, failed_tc_lst in failed_cases.items():
        lib_str_count = library_curd.get_library_string_count(lib_name)
        lib_str_count_dict[lib_name] = lib_str_count
        # 特征收录的原因
        if lib_str_count is None:
            # 没有收录
            not_recorded_libraries.append(lib_name)
        elif lib_str_count == 0:
            recorded_but_no_str_libraries.append(lib_name)
        elif lib_str_count < 10:
            recorded_but_less_str_libraries.append(lib_name)
        # 测试用例的原因
        else:
            failed_tc_lst: Tuple[TestCase, AnalysisResult, AnalysisResultCheck]
            for tc, result, result_check in failed_tc_lst:
                # 没有特征？文件过小？其他原因？
                target_binary:TargetBinary = result.analysis_data.target_binary
                strings_to_match = filter_strings_to_match(target_binary)
                if len(strings_to_match) < 10:
                    unclassified_test_cases.append(tc)
                elif len(strings_to_match) < 25:
                    tc_with_strings_to_match_lt_10.append(tc)
                elif len(strings_to_match) < 50:
                    tc_with_strings_to_match_lt_25.append(tc)
                else:
                    unclassified_test_cases.append(tc)


    print(f'----- classification -----')
    print(f"Total libraries not recorded: {len(not_recorded_libraries)}\n"
          f"Total libraries recorded but no strings: {len(recorded_but_no_str_libraries)}\n"
          f"Total libraries recorded but less than 10 strings: {len(recorded_but_less_str_libraries)}\n")

    print(f"Total test cases with strings to match < 10: {len(tc_with_strings_to_match_lt_10)}\n"
            f"Total test cases with strings to match < 25: {len(tc_with_strings_to_match_lt_25)}\n"
            f"Total test cases with strings to match < 50: {len(tc_with_strings_to_match_lt_50)}\n")
    print(f"Total unclassified test cases: {len(unclassified_test_cases)}\n")

    print(f"others samples")
    for tc in unclassified_test_cases[:10]:
        print(tc.reused_libraries[0].name)
        print(f"lib str count: {lib_str_count_dict.get(tc.reused_libraries[0].name, 'N/A')}")
        print(f"\t{tc.test_binary.relative_path}")
        print(f"\t{tc.test_binary.sha256}")
        print(f"\t{tc.test_binary.file_size_kb}")

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

def _plot_feature_matching_top_n_effectiveness_figure(effectiveness_dict):
    """
    绘制特征匹配效果分析图表

    Parameters:
    effectiveness_dict: dict, 格式为 {top_n: {"precision": float, "recall": float, "f1_score": float}}
    """

    # 设置学术论文风格
    plt.style.use('seaborn-v0_8-whitegrid')  # 使用学术风格
    rcParams['font.family'] = 'serif'
    rcParams['font.size'] = 12
    rcParams['axes.labelsize'] = 14
    rcParams['axes.titlesize'] = 16
    rcParams['xtick.labelsize'] = 12
    rcParams['ytick.labelsize'] = 12
    rcParams['legend.fontsize'] = 12

    # 提取数据并转换键为整数
    top_n_values = sorted([int(k) for k in effectiveness_dict.keys()])
    precision_values = [effectiveness_dict[str(top_n)]['precision'] for top_n in top_n_values]
    recall_values = [effectiveness_dict[str(top_n)]['recall'] for top_n in top_n_values]
    f1_values = [effectiveness_dict[str(top_n)]['f1_score'] for top_n in top_n_values]

    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    # 绘制三条线，使用插值让线条更加流畅
    from scipy.interpolate import make_interp_spline

    # 为了让线条更流畅，创建更密集的x点进行插值
    x_smooth = np.linspace(min(top_n_values), max(top_n_values), 300)

    # 使用样条插值让线条更流畅
    precision_smooth = make_interp_spline(top_n_values, precision_values, k=3)(x_smooth)
    recall_smooth = make_interp_spline(top_n_values, recall_values, k=3)(x_smooth)
    f1_smooth = make_interp_spline(top_n_values, f1_values, k=3)(x_smooth)

    # 绘制流畅的线条
    ax.plot(x_smooth, precision_smooth, 'b-', linewidth=2.5, label='Precision', alpha=0.8)
    ax.plot(x_smooth, recall_smooth, 'r-', linewidth=2.5, label='Recall', alpha=0.8)
    ax.plot(x_smooth, f1_smooth, 'g-', linewidth=2.5, label='F1-Score', alpha=0.8)

    # 在原始数据点上添加小标记点（可选，让数据点更明显）
    ax.scatter(top_n_values, precision_values, color='blue', s=15, alpha=0.6, zorder=5)
    ax.scatter(top_n_values, recall_values, color='red', s=15, alpha=0.6, zorder=5)
    ax.scatter(top_n_values, f1_values, color='green', s=15, alpha=0.6, zorder=5)

    # 设置坐标轴
    ax.set_xlabel('Top-N Results', fontweight='bold')
    ax.set_ylabel('Performance (%)', fontweight='bold')

    # 设置坐标轴范围和刻度
    ax.set_xlim(1, max(top_n_values))
    ax.set_ylim(0, 100)

    # 设置x轴刻度，确保显示关键点
    x_ticks = list(range(1, max(top_n_values) + 1, 10))  # 每10个显示一个刻度
    if max(top_n_values) not in x_ticks:
        x_ticks.append(max(top_n_values))
    ax.set_xticks(x_ticks)

    # 设置y轴刻度
    ax.set_yticks(range(0, 101, 10))

    # 添加网格
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)  # 将网格放在数据线后面

    # 添加图例
    ax.legend(loc='best', frameon=True, fancybox=True, shadow=True)

    # 优化布局
    plt.tight_layout()

    # 显示图表
    plt.show()

    # 如果需要保存图表，可以取消注释以下行
    # plt.savefig('effectiveness_analysis.pdf', dpi=300, bbox_inches='tight')
    # plt.savefig('effectiveness_analysis.png', dpi=300, bbox_inches='tight')

    print("建议的图表标题：Performance Metrics vs Top-N Results in Binary Third-party Component Detection")
    print("图表已生成，如需保存请取消注释相应代码行")


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