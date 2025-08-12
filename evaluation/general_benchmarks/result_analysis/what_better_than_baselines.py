from evaluation.general_benchmarks.interface import EvaluationReport



result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/binary_ai/evaluation_report_2025-07-30-12-54-29_converted_reanalyzed.json"
binaryai_report = EvaluationReport.load_from_file(result_path)


result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours_105_0806/evaluation_report_reanalyzed.json"
our_report = EvaluationReport.load_from_file(result_path)

count = 0
for our_result_check,binaryai_result_check in zip(our_report.evaluation_results_check, binaryai_report.evaluation_results_check):
    if not our_result_check.hs_fn and binaryai_result_check.hs_fn:
        count += 1
        # print(our_result_check.binary_hash, our_result_check.binary_size_kb)
        # print(binaryai_result_check.binary_hash, binaryai_result_check.binary_size_kb)
print(count)