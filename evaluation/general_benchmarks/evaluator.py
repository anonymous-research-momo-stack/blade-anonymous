import copy
import json
import os.path
import time
from typing import List

from loguru import logger

from app.interface import AnalysisResult, AnalysisData, TargetBinary
from app.services.tpl_detection.batch_detection_workflow import BatchDetectionWorkflow
from app.services.tpl_detection.detection_workflow import DetectionWorkflow
from evaluation.general_benchmarks.interface import EvaluationConfig, Benchmark, EvaluationReport, AnalysisResultCheck, \
    ResearchQuestionData, EffectivenessData, EfficiencyData, AblationData, CostData, BenchmarkSummary


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
    def run_failed_cases(self, reference_report_path: str, *args, **kwargs):
        report = EvaluationReport.load_from_file(reference_report_path)
        self.benchmark = copy.deepcopy(self.benchmark)


        # Filter failed test cases (missed detections)
        failed_hashes = [check.binary_hash for check in report.evaluation_results_check if not check.perfect]

        # Further filter: only analyze one case per identical binary name for speed
        filtered_test_cases = []
        filtered_test_case_names = set()
        for tc in self.benchmark.test_cases:
            if tc.test_binary.sha256 in failed_hashes and tc.test_binary.original_name not in filtered_test_case_names:
                filtered_test_cases.append(tc)
                filtered_test_case_names.add(tc.test_binary.original_name)

        # Replace test cases and analyze
        self.benchmark.test_cases = filtered_test_cases
        self.benchmark.summary = BenchmarkSummary(
            test_case_num = len(self.benchmark.test_cases),
            covered_library_num = len(set(lib.name for tc in self.benchmark.test_cases for lib in tc.reused_libraries)),
        )
        print(len(self.benchmark.test_cases))
        self.run_benchmark(*args, **kwargs)

    def run_benchmark(self, analyze_context: bool = False):
        """
        Run benchmark to obtain results
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
            logger.info("Analyzing software context...")
            context = self.workflow.analyze_context(self.evaluation_config.test_case_dir)
            self.report.software_context = context

        logger.info(f"Start running test cases")
        results = self.batch_detection_workflow.run_batch(absolute_paths, software_context=context)
        total_time = time.perf_counter() - start_time
        self.report.finished_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time + total_time))
        self.report.evaluation_results = results

        # 生成RQ数据
        logger.info("Analyzing test results")
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
        Check results and compare with Ground Truth
        :return:
        """
        ground_truth_dict = {test_case.test_binary.sha256: test_case.reused_libraries for test_case in
                             self.benchmark.test_cases}
        file_size_kb_dict = {test_case.test_binary.sha256: test_case.test_binary.file_size_kb for test_case in
                                self.benchmark.test_cases}
        results_check_lst = []
        for result in evaluation_results:
            ground_truth_reused_libraries = ground_truth_dict.get(result.binary_sha256, [])

            # Use a set to track matched GT libraries to avoid duplicate matches
            matched_gt_libraries = set()
            detected_gt_libraries = []

            tp_library_names = []
            redundant_tp_library_names = []
            fp_library_names = []

            # Compare detected library names with Ground Truth
            for detected_lib in result.detected_libraries:
                # Skip GCC
                if detected_lib.name.startswith('gcc'):
                    continue

                tp = False
                already_matched_before = False
                # Iterate over all GT libraries to find a match
                for i, gt_lib in enumerate(ground_truth_reused_libraries):

                    # Exact match with Ground Truth name
                    if self._normalize_lib_name(detected_lib.name) == self._normalize_lib_name(gt_lib.name):
                        detected_gt_libraries.append(gt_lib)
                        tp = True

                    # Match with 'lib' prefix variant
                    elif self._normalize_lib_name(detected_lib.name) == self._normalize_lib_name('lib' + gt_lib.name) or self._normalize_lib_name('lib' + detected_lib.name) == self._normalize_lib_name(gt_lib.name):
                        detected_gt_libraries.append(gt_lib)
                        tp = True

                    # Match with any alternative names of the Ground Truth library
                    elif self._normalize_lib_name(detected_lib.name) in [self._normalize_lib_name(lib_name) for lib_name
                                                                         in gt_lib.other_names]:
                        detected_gt_libraries.append(gt_lib)
                        tp = True

                    # If TP, break and record the matched GT library
                    if tp == True:
                        if i in matched_gt_libraries:
                            already_matched_before = True
                        else:
                            matched_gt_libraries.add(i)
                        break

                if tp:
                    # Do not add duplicate TP results if already matched before
                    if not already_matched_before:
                        tp_library_names.append(detected_lib.name)
                    else:
                        redundant_tp_library_names.append(detected_lib.name)
                else:
                    fp_library_names.append(detected_lib.name)

            # Any unmatched Ground Truth libraries are considered FN
            undetected_gt_libraries = [gt_lib for i, gt_lib in enumerate(ground_truth_reused_libraries)
                                       if i not in matched_gt_libraries]

            fn_library_names = [lib.name for lib in undetected_gt_libraries]
            # Generate AnalysisResultCheck object
            has_fn = len(fn_library_names) > 0  # Any false negatives
            has_fp = len(fp_library_names) > 0
            analysis_result_check = AnalysisResultCheck(
                binary_name=result.binary_name,
                binary_path=result.binary_path,
                binary_hash=result.binary_sha256,
                binary_size_kb=file_size_kb_dict.get(result.binary_sha256, 0),  # File size
                succeed= result.error_message is None,  # Whether succeeded
                err_msg=result.error_message,  # Error message
                ground_truth_lib_names=[lib.name for lib in ground_truth_reused_libraries],  # Ground Truth library names
                detected_lib_names=[lib.name for lib in result.detected_libraries],  # Detected library names
                result_count=len(result.detected_libraries),
                tp_count=len(tp_library_names),  # True positives count
                redundant_tp_count=len(redundant_tp_library_names), # Redundant true positives count
                fp_count=len(fp_library_names),  # False positives count
                fn_count=len(fn_library_names),  # False negatives count
                perfect= not(has_fn or has_fp),  # Perfect if no FN and no FP
                hs_fn=has_fn,  # Has false negatives
                hs_fp=has_fp,  # Has false positives
                hs_rd_tp= len(redundant_tp_library_names) > 0,  # Has redundant true positives
                has_multi_results= len(result.detected_libraries) > 1,  # Has multiple detection results
                no_results=len(result.detected_libraries)==0,
                tp_lib_names=tp_library_names,  # True positive library names
                redundant_tp_lib_names=redundant_tp_library_names,  # Redundant true positive names
                fp_lib_names=fp_library_names,  # False positive library names
                fn_lib_names=fn_library_names,  # False negative library names
            )
            results_check_lst.append(analysis_result_check)
        return results_check_lst

    def analyze_result(self,
                    evaluation_results: List[AnalysisResult],
                    evaluation_duration: float,
                    input_token_price_per_1M: float=0.8,  # 每百万输入token的价格, OpenAI GPT-4.1 mini
                    cached_input_token_price_per_1M: float=0.2,  # 每百万输入token的价格, OpenAI GPT-4.1  mini
                    output_token_price_per_1M: float=3.2,  # 每百万输出token的价格, OpenAI GPT-4.1  mini
                    ignore_failed_cases: bool = False,  # 是否忽略失败的测试用例
                    ) -> tuple[list[AnalysisResultCheck], ResearchQuestionData]:
        """
        Generate report
        1. Effectiveness
        2. Efficiency
        3. Cost

        :return:
        """
        # Validate results
        logger.info("Checking results...")
        if ignore_failed_cases:
            evaluation_results = [result for result in evaluation_results if result.error_message is None]

        results_check_lst = self.check_result(evaluation_results)

        # RQ 1, Effectiveness
        print(f"Calculating RQ1 Effectiveness...")
        effectiveness = self._cal_effectiveness(results_check_lst)
        print(f"RQ1 Effectiveness done: {effectiveness}, calculating effectiveness by compile configs...")
        gcc_x86_effectiveness, gcc_arm_effectiveness, clang_x86_64_effectiveness = self._cal_effectiveness_group_by_compile_config(results_check_lst)
        print(f"RQ1 Calculating effectiveness by file sizes")
        size_lt_1000_effectiveness, size_lt_500_effectiveness, size_lt_100_effectiveness = self._cal_effectiveness_group_by_file_size(results_check_lst)

        # RQ 2 Ablation study
        print(f"Calculating RQ2 Effectiveness ablation study...")
        effectiveness_ablation_study = self._cal_ablation_data(evaluation_results)

        # RQ 3 Efficiency and cost
        print(f"Calculating RQ3 Efficiency and Cost...")
        efficiency = self._cal_efficiency(evaluation_results,
                                         evaluation_duration,
                                         input_token_price_per_1M,
                                         output_token_price_per_1M)
        cost = self._cal_cost(
                evaluation_results,
                input_token_price_per_1M,
                cached_input_token_price_per_1M,
                output_token_price_per_1M
        )

        rq_data = ResearchQuestionData(
            effectiveness=effectiveness,
            gcc_x86_effectiveness=gcc_x86_effectiveness,
            gcc_arm_effectiveness=gcc_arm_effectiveness,
            clang_x86_64_effectiveness=clang_x86_64_effectiveness,
            size_lt_1000kb_effectiveness=size_lt_1000_effectiveness,
            size_lt_500kb_effectiveness=size_lt_500_effectiveness,
            size_lt_100kb_effectiveness=size_lt_100_effectiveness,
            effectiveness_ablation_study=effectiveness_ablation_study,
            efficiency=efficiency,
            cost=cost,
        )
        print(f"All research question data computed: {rq_data}")
        return results_check_lst, rq_data

    def _correct_evaluation_results(self, evaluation_results, benchmark_test_cases):
        # 1. Build a benchmark index (by sha256 or relative_path)
        benchmark_dict = {tc.test_binary.sha256: tc for tc in benchmark_test_cases}

        # 2. Remove: filter evaluation_results to keep only cases existing in the benchmark
        corrected_results = []
        existing_sha256s = set()

        for result in evaluation_results:
            if result.binary_sha256 =='d3626b4036f93dc0efb61dd0c4d9df87c78a076a599cd8fd83d8bdbd45d52820':
                print()
            if result.binary_sha256 in benchmark_dict:
                corrected_results.append(result)
                existing_sha256s.add(result.binary_sha256)

        # 3. Complement: create failed results for cases present in benchmark but missing from evaluation_results
        for sha256, test_case in benchmark_dict.items():
            if sha256 =='d3626b4036f93dc0efb61dd0c4d9df87c78a076a599cd8fd83d8bdbd45d52820':
                print()
            if sha256 not in existing_sha256s:
                # Create a failed AnalysisResult
                failed_result = AnalysisResult(
                    binary_name=test_case.test_binary.original_name,
                    binary_path=test_case.test_binary.relative_path,
                    binary_sha256=sha256,
                    analysis_data=AnalysisData(
                        target_binary=TargetBinary(
                            binary_name=test_case.test_binary.original_name,
                            relative_path=test_case.test_binary.relative_path,
                            hash_sha256=sha256,
                            file_size_kb=test_case.test_binary.file_size_kb,
                        )
                    ),
                    succeed=False,
                    error_message="Auto added! Analysis failed: No result found for this test case.",
                )
                corrected_results.append(failed_result)

        return corrected_results

    def reanalyze_report(self, evaluation_report_save_path:str,
                         new_report_save_path:str=None,
                         ignore_failed_cases:bool=False):
        if not new_report_save_path:
            new_report_save_path = evaluation_report_save_path[:-5] + '_reanalyzed.json'

        # Load
        report = EvaluationReport.load_from_file(evaluation_report_save_path)

        # Align test cases with benchmark
        corrected_results = self._correct_evaluation_results(
            report.evaluation_results,
            self.benchmark.test_cases
        )

        # Re-analyze
        evaluation_duration = report.research_question_data.efficiency.total_actual_duration if report.research_question_data else 0.0
        results_check_lst, rq_data = self.analyze_result(
            evaluation_results=corrected_results,
            evaluation_duration=evaluation_duration,
            input_token_price_per_1M=self.evaluation_config.input_token_price_per_1M,  # price per 1M input tokens
            output_token_price_per_1M=self.evaluation_config.output_token_price_per_1M,
            ignore_failed_cases=ignore_failed_cases,
        )

        # Update
        report.evaluation_results = corrected_results # Update detection results
        report.evaluation_results_check = results_check_lst # Update checks
        report.research_question_data = rq_data # Update RQ data

        # Update statistics
        report.succeed_count = sum(1 for result in corrected_results if result.error_message is None)
        report.failed_count = sum(1 for result in corrected_results if result.error_message is not None)

        # Save
        report.dump(new_report_save_path)
        return report

    def analyze_baseline_result(self, evaluation_result_path, result_checks_save_path:str = None):
        if not result_checks_save_path:
            result_checks_save_path = evaluation_result_path[:-5] + '_checks.json'

        # Load results
        with open(evaluation_result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        evaluation_results = [AnalysisResult.init_from_dict(result) for result in data]

        # Check correctness against Ground Truth
        result_check_lst = self.check_result(evaluation_results)

        with open(result_checks_save_path, "w", encoding="utf-8") as f:
            data = [check.customer_serialize() for check in result_check_lst]
            json.dump(data, f, indent=4, ensure_ascii=False)

        # Calculate evaluation metrics
        effectiveness = self._cal_effectiveness(result_check_lst)

        # Preview metrics
        print(effectiveness)

    # Normalize library name string
    def _normalize_lib_name(self, lib_name: str):
        return lib_name.lower().strip().replace('-','_').replace('.','_')

    def _cal_effectiveness(self, result_check_lst):
        # TP, FP, FN
        tp_count = sum(len(check.tp_lib_names) for check in result_check_lst)
        fp_count = sum(len(check.fp_lib_names) for check in result_check_lst)
        fn_count = sum(len(check.fn_lib_names) for check in result_check_lst)
        # Precision, Recall, F1-Score (percentage, two decimals)
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

    def _cal_effectiveness_group_by_compile_config(self,result_check_lst):
        gcc_x86 = []
        gcc_arm = []
        clang_x86_64 = []
        for check in result_check_lst:
            if "x86_64-gcc" in check.binary_path:
                gcc_x86.append(check)
            elif "arm_64-gcc" in check.binary_path:
                gcc_arm.append(check)
            elif "x86_64-clang" in check.binary_path:
                clang_x86_64.append(check)
            else:
                logger.warning(f"Unknown compile config for binary {check.binary_name}, path: {check.binary_path}")
                continue

        gcc_x86_effectiveness = self._cal_effectiveness(gcc_x86)
        gcc_arm_effectiveness = self._cal_effectiveness(gcc_arm)
        clang_x86_64_effectiveness = self._cal_effectiveness(clang_x86_64)

        return gcc_x86_effectiveness, gcc_arm_effectiveness, clang_x86_64_effectiveness

    def _cal_effectiveness_group_by_file_size(self,result_check_lst):
        size_lt_1000= []  # Less than 1MB
        size_lt_500 = []
        size_lt_100 = []
        for check in result_check_lst:
            if check.binary_size_kb < 1000:  # Less than 1MB
                size_lt_1000.append(check)
            if check.binary_size_kb < 500:
                size_lt_500.append(check)
            if check.binary_size_kb < 100:
                size_lt_100.append(check)

        size_lt_1000_effectiveness = self._cal_effectiveness(size_lt_1000)
        size_lt_500_effectiveness = self._cal_effectiveness(size_lt_500)
        size_lt_100_effectiveness = self._cal_effectiveness(size_lt_100)

        return size_lt_1000_effectiveness, size_lt_500_effectiveness, size_lt_100_effectiveness

    def _cal_ablation_data(self, evaluation_results):
        # Ablate agent full analysis, keep feature-matching top_n
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # Keep only libraries identified via feature matching
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis = self._cal_effectiveness(results_check_lst)

        # Ablate agent full analysis, feature matching only top_1
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # Keep only libraries identified via feature matching
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:1]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_1 = self._cal_effectiveness(results_check_lst)

        # Ablate agent full analysis, feature matching only top_2
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # Keep only libraries identified via feature matching
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:2]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_2 = self._cal_effectiveness(results_check_lst)

        # Ablate agent full analysis, feature matching only top_3
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # Keep only libraries identified via feature matching
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:3]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_3 = self._cal_effectiveness(results_check_lst)

        # Ablate agent full analysis, feature matching only top_4
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # Keep only libraries identified via feature matching
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries
                                                    if self.workflow.feature_matching_detector.method_name in tpl.identify_methods][:4]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        effectiveness_wo_agent_analysis_top_4 = self._cal_effectiveness(results_check_lst)

        # Ablation 1: Remove Agent TPL analysis
        # Compute results after ablation
        evaluation_results_wo_agent_tpl_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_tpl_analysis:
            # Filter out libraries detected only by Agent TPL analysis; keep those identified by feature matching
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.detected_libraries
                                           if self.workflow.feature_matching_detector.method_name in tpl.identify_methods]
        # 重新检查
        results_check_lst = self.check_result(evaluation_results_wo_agent_tpl_analysis)

        # Recalculate effectiveness
        effectiveness_wo_agent_tpl_analysis = self._cal_effectiveness(results_check_lst)

        # Ablation 2: Remove validation steps
        # Remove validation step 1
        # Compute results after ablation
        evaluation_results_wo_validation_step_1 = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_validation_step_1:
            # Keep candidates that are not redundant
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries if not tpl.is_redundant]

        results_check_lst = self.check_result(evaluation_results_wo_validation_step_1)

        effectiveness_wo_validation_step_1 = self._cal_effectiveness(results_check_lst)

        # Remove validation step 2
        evaluation_results_wo_validation_step_2 = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_validation_step_2:
            # Keep candidates that are reasonable
            evaluation_result.detected_libraries =  [tpl for tpl in evaluation_result.analysis_data.all_candidate_libraries if tpl.is_reasonable]

        results_check_lst = self.check_result(evaluation_results_wo_validation_step_2)

        effectiveness_wo_validation_step_2 = self._cal_effectiveness(results_check_lst)

        # Ablate feature matching (placeholders if needed for future)



        # Remove all Agent validation steps
        evaluation_results_wo_validation_step_1_and_2 = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_validation_step_1_and_2:
            # Do not restrict redundancy or reasonableness; keep all candidates
            evaluation_result.detected_libraries = evaluation_result.analysis_data.all_candidate_libraries

        results_check_lst = self.check_result(evaluation_results_wo_validation_step_1_and_2)
        effectiveness_wo_validation_step_1_and_2 = self._cal_effectiveness(results_check_lst)

        # Pure semantic reasoning results
        evaluation_results_wo_agent_analysis = copy.deepcopy(evaluation_results)
        for evaluation_result in evaluation_results_wo_agent_analysis:
            # Keep only TPL analysis results
            evaluation_result.detected_libraries = [tpl for tpl in evaluation_result.analysis_data.tpl_analysis_results]

        results_check_lst = self.check_result(evaluation_results_wo_agent_analysis)
        only_agent_analysis_wt_validation = self._cal_effectiveness(results_check_lst)

        # Summary
        # 1. Remove semantic info: keep matching info + reasoning COT
        # 2. Remove matching info: keep semantic info + reasoning COT
        # 3. Remove reasoning COT: semantic info + matching info + basic prompt (separate experiment)

        # 4. Remove inference COT: semantic info + matching info + validation COT
        # 5. Remove validation COT: semantic info + matching info + inference COT

        return AblationData(
            wo_agent_analysis=effectiveness_wo_agent_analysis,
            wo_agent_analysis_top_1=effectiveness_wo_agent_analysis_top_1,
            wo_agent_analysis_top_2=effectiveness_wo_agent_analysis_top_2,
            wo_agent_analysis_top_3=effectiveness_wo_agent_analysis_top_3,
            wo_agent_analysis_top_4=effectiveness_wo_agent_analysis_top_4, # Remove matching info: semantic info + reasoning COT
            only_agent_analysis_wt_validation=only_agent_analysis_wt_validation, # Semantic reasoning only, no matching
            wo_agent_tpl_analysis=effectiveness_wo_agent_tpl_analysis, # 4. Remove inference COT: semantic + matching + validation COT
            wo_validation_step_1=effectiveness_wo_validation_step_1,
            wo_validation_step_2=effectiveness_wo_validation_step_2,
            wo_validation_step_1_and_2=effectiveness_wo_validation_step_1_and_2, # 5. Remove validation COT: semantic + matching + inference COT
        )

    def _cal_efficiency(self,
                        evaluation_results,
                        evaluation_duration,
                        input_token_price_per_1M,
                        output_token_price_per_1M):
        # ----- File size -----
        total_file_size = sum(result.analysis_data.target_binary.file_size_kb for result in evaluation_results)  # Total file size
        average_file_size = total_file_size / len(evaluation_results) if evaluation_results else 0.0  # Average file size

        # ----- Time overhead -----
        # Theoretical time overhead
        total_theoretical_duration = sum(result.analysis_data.durations.get('total', 0) for result in evaluation_results)  # Total detection time
        average_theoretical_duration = total_theoretical_duration / len(evaluation_results) if evaluation_results else 0.0  # Average detection time

        # Actual detection time
        total_actual_duration = evaluation_duration  # Actual total detection time
        average_actual_duration = evaluation_duration / len(evaluation_results) if evaluation_results else 0.0  # Actual average detection time


        # Time breakdown for each step
        step_total_theoretical_duration = {}
        for result in evaluation_results:
            for step, duration in result.analysis_data.durations.items():
                if step not in step_total_theoretical_duration:
                    step_total_theoretical_duration[step] = 0.0
                step_total_theoretical_duration[step] += duration

        # Correct theoretical total time in case of inconsistencies
        total = 0.0
        for step, duration in step_total_theoretical_duration.items():
            if step != 'total' and not step.startswith('_'):
                total += duration
        step_total_theoretical_duration['total'] = total_theoretical_duration = total

        # Calculate proportions
        step_total_theoretical_duration_proportions = {}
        for step, duration in step_total_theoretical_duration.items():
            step_total_theoretical_duration_proportions[step] = round((duration / total_theoretical_duration) * 100, 2) if total_theoretical_duration > 0 else 0.0

        # Calculate LLM time
        all_llm_duration = 0.0
        for result in evaluation_results:
            for detector_name, cost_dict in result.analysis_data.costs.items():
                if 'time' in cost_dict:
                    llm_duration = sum(cost_dict.get('time', []))
                    all_llm_duration += llm_duration

        rq_3_data = EfficiencyData(
            total_file_size_kb=total_file_size,
            average_file_size_kb=average_file_size,
            total_theoretical_duration=total_theoretical_duration,
            average_theoretical_duration=average_theoretical_duration,
            total_actual_duration=total_actual_duration,
            average_actual_duration=average_actual_duration,
            step_total_theoretical_duration=step_total_theoretical_duration,
            duration_breakdown=step_total_theoretical_duration_proportions,
            llm_duration=all_llm_duration
        )
        return rq_3_data

    def _cal_cost(self,
                        evaluation_results,
                        input_token_price_per_1M,
                  cached_input_token_price_per_1M,
                        output_token_price_per_1M):
        # ----- Cost -----
        total_uncached_input_tokens = 0
        total_cached_input_tokens = 0
        total_input_tokens = 0
        output_token_count = 0
        total_cost = 0.0
        for result in evaluation_results:
            for agent_name, cost_dict in result.analysis_data.costs.items():
                # total input tokens
                input_tokens = sum(cost_dict.get('input_tokens', []))
                total_input_tokens += input_tokens

                # cached tokens
                cached_tokens = sum(cost_dict.get('cached_tokens', []))
                total_cached_input_tokens += cached_tokens

                # uncached tokens
                uncached_tokens = input_tokens - cached_tokens
                total_uncached_input_tokens += uncached_tokens

                # output tokens
                output_tokens = sum(cost_dict.get('output_tokens', []))
                output_token_count += output_tokens

        # Cost
        uncached_input_cost = total_uncached_input_tokens /1_000_000 * input_token_price_per_1M  # Uncached input token cost
        cached_input_cost = total_cached_input_tokens /1_000_000 * cached_input_token_price_per_1M

        input_cost = uncached_input_cost + cached_input_cost
        output_cost = (output_token_count / 1_000_000) * output_token_price_per_1M
        total_cost += input_cost + output_cost

        average_cost = total_cost / len(evaluation_results) if evaluation_results else 0.0  # Average cost

        cost_data = CostData(
            uncached_input_token_count=total_uncached_input_tokens,
            cached_input_token_count=total_cached_input_tokens,
            total_input_token_count=total_input_tokens,
            output_token_count=output_token_count,
            total_token_count=total_input_tokens + output_token_count,

            uncached_input_cost=uncached_input_cost,
            cached_input_cost=cached_input_cost,
            total_input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            average_cost=average_cost
        )

        return cost_data

