import json

from evaluation.general_benchmarks.interface import SimpleEvaluationReport

simple_report_json_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours_102_mini_all_0831/evaluation_report_simple.json"
with open(simple_report_json_path,'r') as f:
    simple_report = json.load(f)

simple_report = SimpleEvaluationReport.init_from_dict(simple_report)


def print_fn_cases(simple_report):
    """
    打印所有包含 hs_fn 的测试用例。
    """
    for check in simple_report.evaluation_results_check:
        if check.hs_fn:
            print(check.binary_name)
            print(f"\tdetected names: {check.detected_lib_names}")
            print(f"\tground_truth names: {check.ground_truth_lib_names}")
            print(f"\ttp_names: {check.tp_lib_names}")
            print(f"\tfp_names: {check.fp_lib_names}")
            print(f"\tfn_names: {check.fn_lib_names}")

def print_fp_cases(simple_report):
    """
    打印所有包含 hs_fp 的测试用例。
    """
    for check in simple_report.evaluation_results_check:
        if check.hs_fp:
            print(check.binary_name)
            print(f"\tdetected names: {check.detected_lib_names}")
            print(f"\tground_truth names: {check.ground_truth_lib_names}")
            print(f"\ttp_names: {check.tp_lib_names}")
            print(f"\tfp_names: {check.fp_lib_names}")
            print(f"\tfn_names: {check.fn_lib_names}")


print_fp_cases(simple_report)
