import copy
import os
import time
from collections import defaultdict
from typing import List, Tuple

from loguru import logger

from app.interface import AnalysisResult
from app.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
from app.tpl_detection.detection_workflow import DetectionWorkflow
from evaluation.conan_benchmark.interface import (
    ConanEvaluationConfig, Benchmark, ConanEvaluationReport,
    ProgramAnalysisResult, ProgramAnalysisResultCheck, DetectedLibrary,
    ConanBenchmarkMeta, TestSoftware, TestBinarySuite, Library, Binary
)

# 导入原有的数据结构用于复用
from evaluation.general_benchmarks.interface import (
    ResearchQuestionData, EffectivenessData, EfficiencyData,
    AblationData, CostData
)


class ConanEvaluator:
    def __init__(self, config: ConanEvaluationConfig):
        self.evaluation_config = config

        # 加载benchmark
        self.benchmark = Benchmark.init_from_dict(self._load_benchmark_data(config.benchmark_file))

        # 初始化检测工作流
        self.workflow = DetectionWorkflow(
            feature_matching_return_top_n=5,
        )
        self.batch_detection_workflow = BatchDetectionWorkflow(
            concurrency=config.concurrency,
            feature_matching_return_top_n=5
        )

        # 初始化报告
        self.report = ConanEvaluationReport(
            evaluation_config=config,
            benchmark=self.benchmark,
        )

    def _load_benchmark_data(self, benchmark_file: str) -> dict:
        """加载benchmark数据"""
        import json
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def run_benchmark(self, analyze_context: bool = True) -> ConanEvaluationReport:
        """运行完整评估"""
        start_time = time.perf_counter()
        self.report.start_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))

        # 分析软件上下文（可选）
        context = None
        if analyze_context:
            logger.info("分析软件上下文...")
            context = self.workflow.analyze_context(self.evaluation_config.benchmark_data_dir)
            self.report.software_context = context

        # 获取要评估的程序套件
        program_suites = self._get_target_program_suites()
        logger.info(f"开始评估 {len(program_suites)} 个程序套件")

        # 逐个评估程序套件
        program_results = []
        for i, (test_software, test_suite) in enumerate(program_suites):
            logger.info(f"评估程序套件 {i + 1}/{len(program_suites)}: {test_software.source_library.name}")
            try:
                result = self.evaluate_program_suite(test_software, test_suite, context)
                program_results.append(result)
            except Exception as e:
                logger.error(f"评估程序套件失败: {test_software.source_library.name}, 错误: {e}")
                continue

        # 记录评估结果
        self.report.program_analysis_results = program_results

        # 计算总时间
        total_time = time.perf_counter() - start_time
        self.report.finished_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time + total_time))

        # 分析结果
        logger.info("分析评估结果...")
        results_check, rq_data = self.analyze_results(program_results, total_time)
        self.report.program_results_check = results_check
        self.report.research_question_data = rq_data

        # 生成benchmark元数据
        self.report.benchmark_meta = self._generate_benchmark_meta()

        logger.info(f"评估完成，总耗时: {total_time:.2f} 秒")
        return self.report

    def _get_target_program_suites(self) -> List[Tuple[TestSoftware, TestBinarySuite]]:
        """获取目标程序套件列表"""
        program_suites = []

        for test_software in self.benchmark.test_software:
            # 检查是否在目标软件列表中
            if (self.evaluation_config.target_software_names and
                    test_software.source_library.name not in self.evaluation_config.target_software_names):
                continue

            for test_suite in test_software.test_binary_suites:
                # 检查是否在目标编译配置中
                if (self.evaluation_config.target_compile_configs and
                        test_suite.compile_config.profile not in self.evaluation_config.target_compile_configs):
                    continue

                # 检查是否满足最小库数量要求
                real_used_libs = [lr for lr in test_suite.library_reuses if lr.is_real_used]
                if len(real_used_libs) < self.evaluation_config.min_reused_lib_num:
                    continue

                program_suites.append((test_software, test_suite))

        # 应用切片
        start = self.evaluation_config.slice_start
        end = len(program_suites) if self.evaluation_config.slice_end == -1 else self.evaluation_config.slice_end
        return program_suites[start:end]

    def evaluate_program_suite(self, test_software: TestSoftware,
                               test_suite: TestBinarySuite,
                               context=None) -> ProgramAnalysisResult:
        """评估单个程序套件"""
        program_id = f"{test_software.source_library.name}_{test_software.source_library.version}_{test_suite.compile_config.profile}"

        # 获取所有二进制文件路径
        binary_paths, binaries = self._resolve_binary_paths(test_suite)

        if not binary_paths:
            logger.warning(f"程序套件 {program_id} 没有找到有效的二进制文件")
            return ProgramAnalysisResult(
                program_id=program_id,
                source_library=test_software.source_library,
                compile_config=test_suite.compile_config,
                analyzed_binaries=[]
            )

        # 批量检测二进制文件
        logger.info(f"批量检测 {len(binary_paths)} 个二进制文件...")
        binary_results = self.batch_detection_workflow.run_batch(binary_paths, software_context=context)

        # 聚合检测结果
        detected_libraries = self._aggregate_detection_results(binary_results)

        # 计算汇总统计
        total_duration = sum(r.analysis_data.durations.get('total', 0) for r in binary_results)
        total_size = sum(r.analysis_data.target_binary.file_size_kb for r in binary_results)
        total_input_tokens = sum(
            sum(cost_dict.get('input_tokens', []))
            for r in binary_results
            for cost_dict in r.analysis_data.costs.values()
        )
        total_output_tokens = sum(
            sum(cost_dict.get('output_tokens', []))
            for r in binary_results
            for cost_dict in r.analysis_data.costs.values()
        )

        # 计算成本
        input_cost = (total_input_tokens / 1_000_000) * self.evaluation_config.input_token_price_per_1M
        output_cost = (total_output_tokens / 1_000_000) * self.evaluation_config.output_token_price_per_1M
        total_cost = input_cost + output_cost

        return ProgramAnalysisResult(
            program_id=program_id,
            source_library=test_software.source_library,
            compile_config=test_suite.compile_config,
            analyzed_binaries=binaries,
            detected_libraries=detected_libraries,
            total_analysis_duration=total_duration,
            total_file_size_kb=total_size,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_cost=total_cost,
            binary_analysis_results=binary_results
        )

    def _resolve_binary_paths(self, test_suite: TestBinarySuite) -> Tuple[List[str], List[Binary]]:
        """解析程序套件中所有二进制文件的绝对路径"""
        paths = []
        binaries = []

        for tpl_name, tpl_binaries in test_suite.binaries.items():
            for binary in tpl_binaries:
                abs_path = os.path.join(self.evaluation_config.benchmark_data_dir, binary.rel_path)
                if os.path.exists(abs_path):
                    paths.append(abs_path)
                    binaries.append(binary)
                else:
                    logger.warning(f"二进制文件不存在: {abs_path}")

        return paths, binaries

    def _aggregate_detection_results(self, binary_results: List[AnalysisResult]) -> List[DetectedLibrary]:
        """聚合同一程序的多个二进制文件检测结果"""
        # 按库名称分组
        lib_groups = defaultdict(list)

        for result in binary_results:
            for lib in result.detected_libraries:
                lib_groups[lib.name].append((lib, result.binary_name))

        # 聚合相同名称的库
        aggregated_libs = []
        for lib_name, lib_instances in lib_groups.items():
            # 合并库信息
            all_libs = [lib for lib, _ in lib_instances]
            source_binaries = [binary_name for _, binary_name in lib_instances]

            # 取最高置信度和最丰富的信息
            best_lib = max(all_libs, key=lambda x: x.confidence if hasattr(x, 'confidence') else 0)

            # 合并identify_methods
            all_methods = set()
            for lib in all_libs:
                if hasattr(lib, 'identify_methods'):
                    all_methods.update(lib.identify_methods)

            # 创建聚合库
            aggregated_lib = DetectedLibrary(
                name=lib_name,
                version=getattr(best_lib, 'version', None),
                confidence=getattr(best_lib, 'confidence', 0.0),
                identify_methods=list(all_methods),
                source_binaries=source_binaries,
                is_reasonable=getattr(best_lib, 'is_reasonable', True),
                is_redundant=getattr(best_lib, 'is_redundant', False),
                description=getattr(best_lib, 'description', '')
            )

            aggregated_libs.append(aggregated_lib)

        return aggregated_libs

    def check_program_results(self, program_results: List[ProgramAnalysisResult]) -> List[ProgramAnalysisResultCheck]:
        """检查程序级结果与Ground Truth的对比"""
        results_check = []

        # 构建Ground Truth映射
        gt_mapping = {}
        for test_software in self.benchmark.test_software:
            for test_suite in test_software.test_binary_suites:
                program_id = f"{test_software.source_library.name}_{test_software.source_library.version}_{test_suite.compile_config.profile}"
                gt_libs = self._extract_ground_truth_libraries(test_suite.library_reuses)
                gt_mapping[program_id] = gt_libs

        for result in program_results:
            gt_libs = gt_mapping.get(result.program_id, [])
            detected_libs = [lib.name for lib in result.detected_libraries]

            # 计算TP, FP, FN
            tp_libs, fp_libs, fn_libs = self._match_detected_with_ground_truth(detected_libs, gt_libs)

            check = ProgramAnalysisResultCheck(
                program_id=result.program_id,
                source_library_name=result.source_library.name,
                compile_config=result.compile_config.profile,
                ground_truth_lib_names=gt_libs,
                detected_lib_names=detected_libs,
                has_fn=len(fn_libs) > 0,
                has_fp=len(fp_libs) > 0,
                tp_lib_names=tp_libs,
                fp_lib_names=fp_libs,
                fn_lib_names=fn_libs,
                total_binaries_analyzed=len(result.analyzed_binaries),
                total_file_size_kb=result.total_file_size_kb
            )

            results_check.append(check)

        return results_check

    def _extract_ground_truth_libraries(self, library_reuses: List) -> List[str]:
        """从LibraryReuse列表中提取实际使用的库名称"""
        gt_libs = []
        for reuse in library_reuses:
            if (reuse.is_real_used and
                    reuse.link_type not in ['static'] and  # 过滤构建工具
                    reuse.library.name not in ['cmake', 'ninja', 'meson', 'autoconf', 'automake', 'm4', 'libtool',
                                               'gnu-config', 'pkgconf', 'flex', 'gperf']):  # 过滤常见构建工具
                gt_libs.append(reuse.library.name)
        return list(set(gt_libs))  # 去重

    def _match_detected_with_ground_truth(self, detected_libs: List[str],
                                          ground_truth_libs: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """匹配检测结果与Ground Truth"""

        # 标准化库名称
        def normalize_name(name: str) -> str:
            return name.lower().strip().replace('-', '_').replace('.', '_')

        gt_normalized = {normalize_name(lib): lib for lib in ground_truth_libs}
        detected_normalized = {normalize_name(lib): lib for lib in detected_libs}

        tp_libs = []
        fp_libs = []
        fn_libs = []

        # 找到TP和FP
        for norm_detected, original_detected in detected_normalized.items():
            if norm_detected in gt_normalized:
                tp_libs.append(original_detected)
            else:
                fp_libs.append(original_detected)

        # 找到FN
        for norm_gt, original_gt in gt_normalized.items():
            if norm_gt not in detected_normalized:
                fn_libs.append(original_gt)

        return tp_libs, fp_libs, fn_libs

    def analyze_results(self, program_results: List[ProgramAnalysisResult],
                        total_duration: float) -> Tuple[List[ProgramAnalysisResultCheck], ResearchQuestionData]:
        """分析评估结果"""

        # 检查结果
        results_check = self.check_program_results(program_results)

        # RQ1: 效果分析
        effectiveness = self._calculate_effectiveness(results_check)

        # RQ2: 消融实验
        effectiveness_ablation = self._calculate_ablation_data(program_results)

        # RQ3: 效率分析
        efficiency = self._calculate_efficiency(program_results, total_duration)

        # RQ4: 成本分析
        cost = self._calculate_cost(program_results)

        rq_data = ResearchQuestionData(
            effectiveness=effectiveness,
            effectiveness_ablation_study=effectiveness_ablation,
            efficiency=efficiency,
            cost=cost
        )

        return results_check, rq_data

    def _calculate_effectiveness(self, results_check: List[ProgramAnalysisResultCheck]) -> EffectivenessData:
        """计算效果指标"""
        tp_count = sum(len(check.tp_lib_names) for check in results_check)
        fp_count = sum(len(check.fp_lib_names) for check in results_check)
        fn_count = sum(len(check.fn_lib_names) for check in results_check)

        precision = round(tp_count / (tp_count + fp_count) * 100, 2) if (tp_count + fp_count) > 0 else 0.0
        recall = round(tp_count / (tp_count + fn_count) * 100, 2) if (tp_count + fn_count) > 0 else 0.0
        f1_score = round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0.0

        return EffectivenessData(
            tp_count=tp_count,
            fp_count=fp_count,
            fn_count=fn_count,
            precision=precision,
            recall=recall,
            f1_score=f1_score
        )

    def _calculate_ablation_data(self, program_results: List[ProgramAnalysisResult]) -> AblationData:
        """计算消融实验数据"""

        # 消融Agent全部分析，只保留特征匹配结果
        def create_ablation_results(filter_func, top_n=None):
            ablation_results = []
            for program_result in program_results:
                # 重新创建程序结果，只使用指定的库
                filtered_libs = []
                for binary_result in program_result.binary_analysis_results:
                    candidate_libs = filter_func(binary_result)
                    if top_n:
                        candidate_libs = candidate_libs[:top_n]
                    for lib in candidate_libs:
                        if lib.name not in [fl.name for fl in filtered_libs]:
                            filtered_libs.append(DetectedLibrary(
                                name=lib.name,
                                version=getattr(lib, 'version', None),
                                confidence=getattr(lib, 'confidence', 0.0),
                                identify_methods=getattr(lib, 'identify_methods', []),
                                source_binaries=[binary_result.binary_name]
                            ))

                ablation_result = copy.deepcopy(program_result)
                ablation_result.detected_libraries = filtered_libs
                ablation_results.append(ablation_result)

            check_results = self.check_program_results(ablation_results)
            return self._calculate_effectiveness(check_results)

        # 定义过滤函数
        feature_matching_filter = lambda br: [lib for lib in br.analysis_data.all_candidate_libraries
                                              if self.workflow.feature_matching_detector.method_name in getattr(lib,
                                                                                                                'identify_methods',
                                                                                                                [])]

        agent_tpl_filter = lambda br: [lib for lib in br.detected_libraries
                                       if self.workflow.feature_matching_detector.method_name in getattr(lib,
                                                                                                         'identify_methods',
                                                                                                         [])]

        non_redundant_filter = lambda br: [lib for lib in br.analysis_data.all_candidate_libraries
                                           if not getattr(lib, 'is_redundant', False)]

        reasonable_filter = lambda br: [lib for lib in br.analysis_data.all_candidate_libraries
                                        if getattr(lib, 'is_reasonable', True)]

        all_candidates_filter = lambda br: br.analysis_data.all_candidate_libraries

        return AblationData(
            wo_agent_analysis=create_ablation_results(feature_matching_filter),
            wo_agent_analysis_top_1=create_ablation_results(feature_matching_filter, 1),
            wo_agent_analysis_top_2=create_ablation_results(feature_matching_filter, 2),
            wo_agent_analysis_top_3=create_ablation_results(feature_matching_filter, 3),
            wo_agent_tpl_analysis=create_ablation_results(agent_tpl_filter),
            wo_validation_step_1=create_ablation_results(non_redundant_filter),
            wo_validation_step_2=create_ablation_results(reasonable_filter),
            wo_validation_step_1_and_2=create_ablation_results(all_candidates_filter)
        )

    def _calculate_efficiency(self, program_results: List[ProgramAnalysisResult],
                              total_duration: float) -> EfficiencyData:
        """计算效率指标"""
        total_file_size = sum(result.total_file_size_kb for result in program_results)
        average_file_size = total_file_size / len(program_results) if program_results else 0.0

        total_theoretical_duration = sum(result.total_analysis_duration for result in program_results)
        average_theoretical_duration = total_theoretical_duration / len(program_results) if program_results else 0.0

        average_actual_duration = total_duration / len(program_results) if program_results else 0.0

        return EfficiencyData(
            total_file_size_kb=total_file_size,
            average_file_size_kb=average_file_size,
            total_theoretical_duration=total_theoretical_duration,
            average_theoretical_duration=average_theoretical_duration,
            total_actual_duration=total_duration,
            average_actual_duration=average_actual_duration,
            duration_breakdown={}  # 可以后续补充详细的时间分解
        )

    def _calculate_cost(self, program_results: List[ProgramAnalysisResult]) -> CostData:
        """计算成本指标"""
        total_input_tokens = sum(result.total_input_tokens for result in program_results)
        total_output_tokens = sum(result.total_output_tokens for result in program_results)
        total_tokens = total_input_tokens + total_output_tokens
        total_cost = sum(result.total_cost for result in program_results)
        average_cost = total_cost / len(program_results) if program_results else 0.0

        return CostData(
            input_token_count=total_input_tokens,
            output_token_count=total_output_tokens,
            total_token_count=total_tokens,
            total_cost=total_cost,
            average_cost=average_cost
        )

    def _generate_benchmark_meta(self) -> ConanBenchmarkMeta:
        """生成benchmark元数据"""
        test_software_num = len(self.benchmark.test_software)
        test_program_suites_num = sum(len(ts.test_binary_suites) for ts in self.benchmark.test_software)

        # 统计涉及的库数量
        all_libs = set()
        total_binaries = 0
        for ts in self.benchmark.test_software:
            for suite in ts.test_binary_suites:
                for reuse in suite.library_reuses:
                    if reuse.is_real_used:
                        all_libs.add(reuse.library.name)
                total_binaries += sum(len(binaries) for binaries in suite.binaries.values())

        return ConanBenchmarkMeta(
            name=self.benchmark.name,
            version=self.benchmark.version,
            test_software_num=test_software_num,
            test_program_suites_num=test_program_suites_num,
            covered_library_num=len(all_libs),
            total_binaries=total_binaries
        )

    def reanalyze_report(self, evaluation_report_save_path: str) -> ConanEvaluationReport:
        """重新分析已保存的评估报告"""
        # 加载报告
        report = ConanEvaluationReport.load_from_file(evaluation_report_save_path)

        # 重新分析结果
        if report.program_analysis_results:
            # 计算总时间（从原报告中获取）
            total_duration = report.research_question_data.efficiency.total_actual_duration if report.research_question_data and report.research_question_data.efficiency else 0.0

            results_check, rq_data = self.analyze_results(report.program_analysis_results, total_duration)

            # 更新报告
            report.program_results_check = results_check
            report.research_question_data = rq_data

        # 保存更新后的报告
        report.dump(evaluation_report_save_path)
        return report


def main():
    """示例用法"""
    # 示例配置
    config = ConanEvaluationConfig(
        benchmark_file="/evaluation/conan_benchmark/benchmark_meta_local/conan_library_benchmark.json",
        benchmark_data_dir="/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/conan_benchmark/conan_libs_builder_output",
        concurrency=5,
        min_reused_lib_num=3,
        target_software_names=[],  # 空表示全部
        target_compile_configs=[],  # 空表示全部
        slice_start=0,
        slice_end=2,  # 只测试前2个程序套件
    )

    # 初始化评估器
    evaluator = ConanEvaluator(config)

    # 运行评估
    report = evaluator.run_benchmark(analyze_context=False)

    # 保存报告
    output_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/conan_evaluation_report.json"
    report.dump(output_path)

    logger.info(f"评估报告已保存到: {output_path}")

    # 打印简要结果
    if report.research_question_data and report.research_question_data.effectiveness:
        eff = report.research_question_data.effectiveness
        logger.info(f"评估结果 - Precision: {eff.precision}%, Recall: {eff.recall}%, F1: {eff.f1_score}%")


if __name__ == '__main__':
    main()