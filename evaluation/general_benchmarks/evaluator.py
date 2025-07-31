import copy
import json
import os.path
import time
from typing import List

import matplotlib.pyplot as plt
from loguru import logger
from matplotlib import rcParams

from app.interface import AnalysisResult
from app.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
from app.tpl_detection.detection_workflow import DetectionWorkflow
from evaluation.general_benchmarks.interface import EvaluationConfig, Benchmark, EvaluationReport, AnalysisResultCheck, \
    ResearchQuestionData, EffectivenessData, EfficiencyData, AblationData, CostData
from evaluation.general_benchmarks.visualization import generate_analysis_report

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
from scipy.interpolate import make_interp_spline


def plot_effectiveness_analysis(effectiveness_dict):
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

class Evaluator:
    def __init__(self, config: EvaluationConfig):
        self.evaluation_config = config

        self.benchmark = Benchmark.load_from_json_file(config.benchmark_file)

        self.workflow = DetectionWorkflow(
            feature_matching_return_top_n=config.feature_matching_top_n,
            use_agent=config.use_agent,
        )
        self.batch_detection_workflow = BatchDetectionWorkflow(concurrency=config.concurrency,
                                                               feature_matching_return_top_n=config.feature_matching_top_n,
                                                               use_agent=config.use_agent,)

        self.evaluation_results = []

        self.report = EvaluationReport(
            evaluation_config=config,
            benchmark=self.benchmark,
        )

    def run_benchmark(self, analyze_context: bool = True):
        """
        运行，以获取结果
        :return:
        """
        relative_paths = [tc.test_binary.relative_path for tc in self.benchmark.test_cases][
                         self.evaluation_config.slice_start:self.evaluation_config.slice_end]
        absolute_paths = [os.path.join(self.evaluation_config.test_case_dir, path) for path in relative_paths]

        # run test cases
        start_time = time.perf_counter()
        self.report.start_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        context = None
        if analyze_context:
            logger.info("分析软件上下文...")
            context = self.workflow.analyze_context(self.evaluation_config.test_case_dir)
            self.report.software_context = context

        logger.info(f"开始运行测试用例")
        results = self.batch_detection_workflow.run_batch(absolute_paths, software_context=context)
        total_time = time.perf_counter() - start_time
        self.report.finished_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time + total_time))
        self.report.evaluation_results = results

        # 生成RQ数据
        logger.info("分析测试结果")
        results_check_lst, rq_data = self.analyze_result(
            evaluation_results=results,
            evaluation_duration=total_time,
            input_token_price_per_1M=self.evaluation_config.input_token_price_per_1M,  # 每百万输入token的价格, OpenAI GPT-4.1
            output_token_price_per_1M=self.evaluation_config.output_token_price_per_1M,
        )
        self.report.evaluation_results_check = results_check_lst
        self.report.research_question_data = rq_data
        logger.info(f"All Done, total time: {total_time:.2f} seconds")

    def check_result(self, evaluation_results: List[AnalysisResult]) -> List[AnalysisResultCheck]:
        """
        检查结果，与Ground Truth进行对比
        :return:
        """
        ground_truth_dict = {test_case.test_binary.sha256: test_case.reused_libraries for test_case in
                             self.benchmark.test_cases}
        results_check_lst = []
        for result in evaluation_results:
            ground_truth_reused_libraries = ground_truth_dict.get(result.binary_sha256, [])

            undetected_gt_libraries = copy.deepcopy(ground_truth_reused_libraries)
            detected_gt_libraries = []

            tp_library_names = []
            fp_library_names = []

            # 检测到的库名称与Ground Truth进行对比
            for detected_lib in result.detected_libraries:
                tp = False
                for gt_lib in undetected_gt_libraries:
                    # 与Ground Truth 名称一致
                    if self.normalize_lib_name(detected_lib.name) == self.normalize_lib_name(gt_lib.name):
                        detected_gt_libraries.append(gt_lib)
                        undetected_gt_libraries.remove(gt_lib)
                        tp = True
                        break
                    # 与Ground Truth 名称的其他名称一致
                    elif self.normalize_lib_name(detected_lib.name) in [self.normalize_lib_name(lib_name) for lib_name
                                                                        in gt_lib.other_names]:
                        detected_gt_libraries.append(gt_lib)
                        undetected_gt_libraries.remove(gt_lib)
                        tp = True
                        break
                # 如果找到了匹配的Ground Truth库，则认为是TP，否则是FP
                if tp:
                    tp_library_names.append(detected_lib.name)
                else:
                    fp_library_names.append(detected_lib.name)

            # 未检测到的Ground Truth库，均认为是FN
            fn_library_names = [lib.name for lib in undetected_gt_libraries]

            # 生成分析结果检查对象
            has_fn = len(fn_library_names) > 0  # 是否有漏报
            has_fp = len(fp_library_names) > 0
            analysis_result_check = AnalysisResultCheck(
                binary_name=result.binary_name,
                binary_path=result.binary_path,
                binary_hash=result.binary_sha256,
                ground_truth_lib_names=[lib.name for lib in ground_truth_reused_libraries],  # Ground Truth 库名称
                detected_lib_names=[lib.name for lib in result.detected_libraries],  # 检测到的库名称
                result_count=len(result.detected_libraries),
                tp_count=len(tp_library_names),  # 检测到的真正库数量
                fp_count=len(fp_library_names),  # 检测到的误报库数量
                fn_count=len(fn_library_names),  # 漏报的库数量
                perfect= not(has_fn or has_fp),  # 是否完美
                hs_fn=has_fn,  # 是否有漏报
                hs_fp=has_fp,  # 是否有误报
                has_multi_results= len(result.detected_libraries) > 1,  # 是否有多个检测结果
                no_results=len(result.detected_libraries)==0,
                tp_lib_names=tp_library_names,  # 真正检测到的库名称
                fp_lib_names=fp_library_names,  # 误报的库名称
                fn_lib_names=fn_library_names,  # 漏报的库名称
            )
            results_check_lst.append(analysis_result_check)
        return results_check_lst

    # 正规化名称
    def normalize_lib_name(self, lib_name: str):
        return lib_name.lower().strip()

    def reanalyze_report(self, evaluation_report_save_path:str):
        # load
        report = EvaluationReport.load_from_file(evaluation_report_save_path)

        # reanalyze
        results_check_lst, rq_data = self.analyze_result(
            evaluation_results=report.evaluation_results,
            evaluation_duration=report.research_question_data.efficiency.total_actual_duration,
            input_token_price_per_1M=self.evaluation_config.input_token_price_per_1M,  # 每百万输入token的价格, OpenAI GPT-4.1
            output_token_price_per_1M=self.evaluation_config.output_token_price_per_1M,
        )

        # update
        report.evaluation_results_check = results_check_lst
        report.research_question_data = rq_data

        # save
        report.dump(evaluation_report_save_path)
        return report

    def analyze_result(self,
                    evaluation_results: List[AnalysisResult],
                    evaluation_duration: float,
                    input_token_price_per_1M: float=2,  # 每百万输入token的价格, OpenAI GPT-4.1
                    output_token_price_per_1M: float=8,  # 每百万输出token的价格, OpenAI GPT-4.1
                    ) -> tuple[list[AnalysisResultCheck], ResearchQuestionData]:
        """
        生成报告
        1. 效果
        2. 效率
        3. 成本

        :return:
        """
        # 检查结果
        logger.info("检查结果...")
        results_check_lst = self.check_result(evaluation_results)

        # RQ 1，效率
        effectiveness = self._cal_effectiveness(results_check_lst)

        # RQ 2 消融实验
        effectiveness_ablation_study = self._cal_ablation_data(evaluation_results)

        # RQ 3 效率和成本
        efficiency = self._cal_efficiency(evaluation_results,
                                         evaluation_duration,
                                         input_token_price_per_1M,
                                         output_token_price_per_1M)
        cost = self._cal_cost(
                evaluation_results,
                input_token_price_per_1M,
                output_token_price_per_1M
        )

        rq_data = ResearchQuestionData(
            effectiveness=effectiveness,
            effectiveness_ablation_study=effectiveness_ablation_study,
            efficiency=efficiency,
            cost=cost,
        )

        return results_check_lst, rq_data

    def analyze_baseline_result(self, evaluation_result_path, result_checks_save_path:str = None):
        if not result_checks_save_path:
            result_checks_save_path = evaluation_result_path[:-5] + '_checks.json'

        # 加载结果
        with open(evaluation_result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        evaluation_results = [AnalysisResult.init_from_dict(result) for result in data]

        # 检查正确性
        result_check_lst = self.check_result(evaluation_results)

        with open(result_checks_save_path, "w", encoding="utf-8") as f:
            data = [check.customer_serialize() for check in result_check_lst]
            json.dump(data, f, indent=4, ensure_ascii=False)

        # 计算评估指标
        effectiveness = self._cal_effectiveness(result_check_lst)

        # 预览评估指标
        print(effectiveness)

    def analyze_feature_matching(self, evaluation_result_path, effectiveness_analysis_result_path:str = None, top_n=10):
        """
        1. top_n 设置为 1到100 之间的时候，召回率和准确率分别是多少？设计为几的时候效果最好？画个图？
        2. 哪几个库经常被误报出来？
        3. 哪几个库在top 100 都测试不出来？

        """

        # 加载结果
        print(f"loading data")
        with open(evaluation_result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 第一个问题：
        effectiveness_dict = {}
        evaluation_results = [AnalysisResult.init_from_dict(result) for result in data['evaluation_results']]

        # 只复制一次
        top_n_evaluation_results = copy.deepcopy(evaluation_results)

        # 从大到小遍历，计算effectiveness
        for top_n in range(top_n, 0, -1):
            # 截取每个结果的前top_n个检测结果
            for result in top_n_evaluation_results:
                result.detected_libraries = result.detected_libraries[:top_n]

            # 检查正确性
            result_check_lst = self.check_result(top_n_evaluation_results)

            # 计算评估指标
            effectiveness = self._cal_effectiveness(result_check_lst)

            # 预览评估指标
            print(top_n, effectiveness)
            effectiveness_dict[top_n] = effectiveness.customer_serialize()

        with open(effectiveness_analysis_result_path, "w", encoding="utf-8") as f:
            json.dump(effectiveness_dict, f, indent=4, ensure_ascii=False)

    def plot_feature_matching_top_n_analysis(self, effectiveness_analysis_result_path):
        """
        绘制特征匹配效果分析图表
        :param effectiveness_analysis_result_path: 效果分析结果文件路径
        """
        # 加载效果分析结果
        with open(effectiveness_analysis_result_path, "r", encoding="utf-8") as f:
            effectiveness_dict = json.load(f)

        # 绘制图表
        plot_effectiveness_analysis(effectiveness_dict)

    def _cal_effectiveness(self, result_check_lst):
        # TP, FP, FN
        tp_count = sum(len(check.tp_lib_names) for check in result_check_lst)
        fp_count = sum(len(check.fp_lib_names) for check in result_check_lst)
        fn_count = sum(len(check.fn_lib_names) for check in result_check_lst)
        # Precision, Recall, F1-Score (百分比，保留两位小数)
        precision = round(tp_count / (tp_count + fp_count) * 100, 2) if (tp_count + fp_count) > 0 else 0.0
        recall = round(tp_count / (tp_count + fn_count) * 100, 2) if (tp_count + fn_count) > 0 else 0.0
        f1_score = round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0.0
        rq_1_data = EffectivenessData(
            tp_count=tp_count,
            fp_count=fp_count,
            fn_count=fn_count,
            precision=precision,
            recall=recall,
            f1_score=f1_score
        )
        return rq_1_data

    def _cal_ablation_data(self, evaluation_results):
        # 消融掉Agent 全部分析, 特征匹配取top_n
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # 只保留检测到的库
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis = self._cal_effectiveness(results_check_lst)

        # 消融掉Agent 全部分析, 且特征匹配只取top_1
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # 只保留检测到的库
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:1]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_1 = self._cal_effectiveness(results_check_lst)

        # 消融掉Agent 全部分析, 且特征匹配只取top_2
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # 只保留检测到的库
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:2]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_2 = self._cal_effectiveness(results_check_lst)

        # 消融掉Agent 全部分析, 且特征匹配只取top_3
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # 只保留检测到的库
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:3]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_3 = self._cal_effectiveness(results_check_lst)

        # 消融实验1： 消融 Agent TPL分析
        # 计算消融后的结果
        evaluation_results_wo_agent_tpl_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_tpl_analysis:
            # 过滤掉 Agent TPL 分析方法检测到的库，即：有特征匹配的就可以。
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.detected_libraries
                                           if self.workflow.feature_matching_detector.method_name in tpl.identify_methods]
        # 重新检查
        results_check_lst = self.check_result(evaluation_results_wo_agent_tpl_analysis)

        # 重新计算effectiveness
        effectiveness_wo_agent_tpl_analysis = self._cal_effectiveness(results_check_lst)

        # 消融实验2： 消融验证步骤
        # 消融验证步骤 1
        # 计算消融后的结果
        evaluation_results_wo_validation_step_1 = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_validation_step_1:
            # 不冗余即可
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries if not tpl.is_redundant]

        results_check_lst = self.check_result(evaluation_results_wo_validation_step_1)

        effectiveness_wo_validation_step_1 = self._cal_effectiveness(results_check_lst)

        # 消融验证步骤 2
        evaluation_results_wo_validation_step_2 = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_validation_step_2:
            # 合理即可
            evaluation_result.detected_libraries =  [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries if tpl.is_reasonable]

        results_check_lst = self.check_result(evaluation_results_wo_validation_step_2)

        effectiveness_wo_validation_step_2 = self._cal_effectiveness(results_check_lst)


        # 消融Agent 全部验证步骤
        evaluation_results_wo_validation_step_1_and_2 = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_validation_step_1_and_2:
            # 不冗余且合理即可
            evaluation_result.detected_libraries = evaluation_result.analysis_data.all_candidate_libraries

        results_check_lst = self.check_result(evaluation_results_wo_validation_step_1_and_2)
        effectiveness_wo_validation_step_1_and_2 = self._cal_effectiveness(results_check_lst)

        return AblationData(
            wo_agent_analysis=effectiveness_wo_agent_analysis,
            wo_agent_analysis_top_1=effectiveness_wo_agent_analysis_top_1,
            wo_agent_analysis_top_2=effectiveness_wo_agent_analysis_top_2,
            wo_agent_analysis_top_3=effectiveness_wo_agent_analysis_top_3,
            wo_agent_tpl_analysis=effectiveness_wo_agent_tpl_analysis,
            wo_validation_step_1=effectiveness_wo_validation_step_1,
            wo_validation_step_2=effectiveness_wo_validation_step_2,
            wo_validation_step_1_and_2=effectiveness_wo_validation_step_1_and_2,
        )

    def _cal_efficiency(self,
                        evaluation_results,
                        evaluation_duration,
                        input_token_price_per_1M,
                        output_token_price_per_1M):
        # ----- 文件大小 -----
        total_file_size = sum(result.analysis_data.target_binary.file_size_kb for result in evaluation_results)  # 总文件大小
        average_file_size = total_file_size / len(evaluation_results) if evaluation_results else 0.0  # 平均文件大小

        # ----- 时间开销 -----
        # 理论实践开销
        total_theoretical_duration = sum(result.analysis_data.durations['total'] for result in evaluation_results)  # 总检测时间
        average_theoretical_duration = total_theoretical_duration / len(evaluation_results) if evaluation_results else 0.0  # 平均检测时间

        # 实际检测时间
        total_actual_duration = evaluation_duration  # 实际总检测时间
        average_actual_duration = evaluation_duration / len(evaluation_results) if evaluation_results else 0.0  # 实际平均检测时间

        # 每个步骤的时间的 break down
        step_total_theoretical_duration = {}
        for result in evaluation_results:
            for step, duration in result.analysis_data.durations.items():
                if step not in step_total_theoretical_duration:
                    step_total_theoretical_duration[step] = 0.0
                step_total_theoretical_duration[step] += duration

        # 计算比例
        step_total_theoretical_duration_proportions = {}
        for step, duration in step_total_theoretical_duration.items():
            step_total_theoretical_duration_proportions[step] = round((duration / total_theoretical_duration) * 100, 2) if total_theoretical_duration > 0 else 0.0

        # 合并break down数据
        duration_breakdown = {}
        for step, (step_total_theoretical_duration, step_proportion) in zip(step_total_theoretical_duration.keys(), step_total_theoretical_duration_proportions.items()):
            duration_breakdown[step] = (step_total_theoretical_duration, step_proportion)


        rq_3_data = EfficiencyData(
            total_file_size_kb=total_file_size,
            average_file_size_kb=average_file_size,
            total_theoretical_duration=total_theoretical_duration,
            average_theoretical_duration=average_theoretical_duration,
            total_actual_duration=total_actual_duration,
            average_actual_duration=average_actual_duration,
            duration_breakdown=duration_breakdown,
        )
        return rq_3_data

    def _cal_cost(self,
                        evaluation_results,
                        input_token_price_per_1M,
                        output_token_price_per_1M):
        # ----- 成本 -----
        input_token_count = 0
        output_token_count = 0
        total_cost = 0.0
        for result in evaluation_results:
            for agent_name, cost_dict in result.analysis_data.costs.items():
                # input token
                input_tokens = sum(cost_dict.get('input_tokens', []))
                input_token_count += input_tokens

                # output token
                output_tokens = sum(cost_dict.get('output_tokens', []))
                output_token_count += output_tokens

                # cost
                input_cost = (input_tokens / 1_000_000) * input_token_price_per_1M
                output_cost = (output_tokens / 1_000_000) * output_token_price_per_1M
                total_cost += input_cost + output_cost

        average_cost = total_cost / len(evaluation_results) if evaluation_results else 0.0  # 平均成本

        cost_data = CostData(
            input_token_count=input_token_count,
            output_token_count=output_token_count,
            total_token_count=input_token_count+output_token_count,
            total_cost=total_cost,
            average_cost=average_cost
        )

        return cost_data

def analyze_baseline():
    # Conan Binaries
    Conan_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark.json"
    Conan_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases"


    benchmark_meta = Conan_benchmark_meta
    benchmark_tc_dir = Conan_test_case_dir


    # 评估配置
    config = EvaluationConfig(
        benchmark_file=benchmark_meta,
        test_case_dir=benchmark_tc_dir,
        concurrency=30,
        slice_start=0,
        slice_end=30,
    )

    # 初始化评估器
    evaluator = Evaluator(config)
    # =============== baselines ==============
    # 经过格式转换的结果
    # ========================================
    # binary ai
    binary_result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/binary_ai/evaluation_report_2025-07-30-10-03-54_converted.json"
    binary_result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/binary_ai/evaluation_report_2025-07-30-12-54-29_converted.json"
    evaluator.analyze_baseline_result(binary_result_path)

def run_feature_matching_only():
    # 分析输入Conan Binaries
    Conan_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark.json"
    Conan_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases"
    Conan_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/feture_matching/evaluation_report.json"

    # 评估输入
    benchmark_meta = Conan_benchmark_meta
    benchmark_tc_dir = Conan_test_case_dir
    # 评估结果
    evaluation_report_save_path = Conan_evluation_report_path
    # 评估结果的分析结果
    effectiveness_analysis_result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/feture_matching/effectiveness_analysis_result.json"

    # 评估配置
    top_n = 50
    config = EvaluationConfig(
        benchmark_file=benchmark_meta,
        test_case_dir=benchmark_tc_dir,
        feature_matching_top_n=top_n,
        use_agent=False,
        concurrency=10,
        slice_start=0,
        slice_end=30,
    )

    # 初始化评估器
    evaluator = Evaluator(config)

    # 评估
    evaluator.run_benchmark(analyze_context=False)
    evaluator.report.dump(evaluation_report_save_path)

    # 分析结果
    evaluator.analyze_feature_matching(evaluation_report_save_path,effectiveness_analysis_result_path,top_n=top_n)

    # 绘图
    # evaluator.plot_feature_matching_top_n_analysis(effectiveness_analysis_result_path)

def main():
    # 41 个常见组件
    Famous_TPL_41_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/benchmark_meta/FTPL50.json"
    Famous_TPL_41_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/FTPL100/decompressed_deb"
    Famous_TPL_41_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/FTPL_41/evaluation_report.json"

    # 车载系统
    CAR_150_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/benchmark_meta/CAR150.json"
    CAR_150_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/BYD"
    CAR_150_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/CAR_150/evaluation_report.json"

    # Debian Binaries
    Debian_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/benchmark_meta/DDE2000.json"
    Debian_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/Benchmarks/DDE2000"
    Debian_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/DDE_2000/evaluation_report.json"

    # Conan Binaries
    Conan_benchmark_meta = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark.json"
    Conan_test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases"
    Conan_evluation_report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/evaluation_report.json"


    benchmark_meta = Conan_benchmark_meta
    benchmark_tc_dir = Conan_test_case_dir
    evaluation_report_save_path = Conan_evluation_report_path

    # 评估配置
    config = EvaluationConfig(
        benchmark_file=benchmark_meta,
        test_case_dir=benchmark_tc_dir,
        feature_matching_top_n=3,
        # use_agent=False,
        concurrency=10,
        slice_start=0,
        slice_end=30,
    )

    # 初始化评估器
    evaluator = Evaluator(config)

    # 评估
    evaluator.run_benchmark(analyze_context=False)
    evaluator.report.dump(evaluation_report_save_path)

    # 重新分析结果
    report = evaluator.reanalyze_report(evaluation_report_save_path)

    # 可视化分析结果
    visualization_html = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/visualization.html"
    generate_analysis_report(report,
                            visualization_html
                             )

if __name__ == '__main__':
    # main()
    run_feature_matching_only()
    # analyze_baseline()