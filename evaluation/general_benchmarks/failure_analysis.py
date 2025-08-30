
import json
import csv
import os

from evaluation.general_benchmarks.interface import SimpleEvaluationReport


def load_report(report_path):
    """加载评估报告"""
    with open(report_path, 'r') as json_file:
        data = json.load(json_file)

    simple_report = SimpleEvaluationReport.init_from_dict(data)
    return simple_report


def preview_failed_cases(simple_report):
    """预览失败的案例"""
    print("=== Failed Cases Preview ===")
    failed_count = 0

    failed_case_name_set = set()
    for check in simple_report.evaluation_results_check:
        if check.binary_name in failed_case_name_set:
            continue
        failed_case_name_set.add(check.binary_name)
        if check.hs_fp and check.hs_fn:
            failed_count += 1
            print(f"""
--------------------------------------------------------------
index: {failed_count}
binary hash: {check.binary_hash}
    binary path:  {check.binary_path}
    binary name:  {check.binary_name}
    file size:    {round(check.binary_size_kb, 2)} KB
    ground truth: {check.ground_truth_lib_names}
    result libs:  {check.detected_lib_names}
    has_fp:      {check.hs_fp}
    has_fn:      {check.hs_fn}
    TP libs:      {check.tp_lib_names}
    FP libs:      {check.fp_lib_names}
    FN libs:      {check.fn_lib_names}
--------------------------------------------------------------
""")

    print(f"\nTotal failed cases: {failed_count}")
    return failed_count


def save_failed_cases_to_csv(simple_report, report_path):
    """将失败案例保存到CSV文件"""
    # 准备CSV文件路径（与原JSON文件在同一目录）
    csv_path = report_path.replace('.json', '_failed_cases.csv')

    # 定义CSV列标题
    headers = [
        # 'binary_hash',
        'binary_path', 'binary_name', 'file_size_kb',
        'ground_truth', 'result_libs', 'has_fp', 'has_fn',
        'tp_libs', 'fp_libs', 'fn_libs'
    ]

    # 收集失败的案例
    failed_cases = []
    failed_case_name_set = set()
    for check in simple_report.evaluation_results_check:
        if not check.perfect and check.hs_fp and check.hs_fn:
            if check.binary_name in failed_case_name_set:
                continue
            failed_case_name_set.add(check.binary_name)
            failed_cases.append({
                # 'binary_hash': check.binary_hash,
                'binary_path': check.binary_path,
                'binary_name': check.binary_name,
                'file_size_kb': round(check.binary_size_kb, 2),
                'ground_truth': '; '.join(check.ground_truth_lib_names) if check.ground_truth_lib_names else '',
                'result_libs': '; '.join(check.detected_lib_names) if check.detected_lib_names else '',
                'has_fp': check.hs_fp,
                'has_fn': check.hs_fn,
                'tp_libs': '; '.join(check.tp_lib_names) if check.tp_lib_names else '',
                'fp_libs': '; '.join(check.fp_lib_names) if check.fp_lib_names else '',
                'fn_libs': '; '.join(check.fn_lib_names) if check.fn_lib_names else ''
            })

    # 写入CSV文件
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(failed_cases)

    print(f"Successfully exported {len(failed_cases)} failed cases to: {csv_path}")
    return csv_path


def main():
    """主函数"""
    report_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_5_mini/evaluation_report_reanalyzed_simple.json"

    try:
        # 加载报告
        print("Loading evaluation report...")
        simple_report = load_report(report_path)
        print("Report loaded successfully!")

        # 预览失败案例
        failed_count = preview_failed_cases(simple_report)

        # 保存到CSV
        if failed_count > 0:
            csv_path = save_failed_cases_to_csv(simple_report, report_path)
            print(f"\nAnalysis complete! CSV file saved at: {csv_path}")
        else:
            print("\nNo failed cases found!")

    except FileNotFoundError:
        print(f"Error: Report file not found at {report_path}")
    except Exception as e:
        print(f"Error occurred: {str(e)}")


if __name__ == "__main__":
    main()
