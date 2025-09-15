import shutil

from evaluation.general_benchmarks.interface import Benchmark, TestCase


def select_sample(benchmark_file, selected_case_file):
    """

        生成一部分数据

        :return:
        """

    benchmark = Benchmark.load_from_json_file(benchmark_file)

    selected_case = []
    main_lib_name_set = set()
    for case in benchmark.test_cases:
        main_lib = case.test_binary.relative_path.split("/")[5]
        if main_lib not in main_lib_name_set:
            main_lib_name_set.add(main_lib)
            selected_case.append(case)
            for lib in case.reused_libraries:
                lib.type = ""
                lib.notes = ""

        if len(selected_case) > 300:
            break

    cases_data = [case.customer_serialize() for case in selected_case]

    with open(selected_case_file, "w") as f:
        import json
        json.dump(cases_data, f, indent=4, ensure_ascii=False)

import os
def copy_files(selected_case_file, test_case_root_dir, output_dir):

    with open(selected_case_file, "r") as f:
        import json
        cases_data = json.load(f)

    test_cases = [TestCase.init_from_dict(data) for data in cases_data]

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    for case in test_cases:
        relative_path = case.test_binary.relative_path
        abs_path = f"{test_case_root_dir}/{relative_path}"

        if os.path.exists(abs_path):
            output_path = f"{output_dir}/{relative_path}"
            this_case_output_dir = os.path.dirname(output_path)
            os.makedirs(this_case_output_dir, exist_ok=True)
            shutil.copyfile(abs_path, output_path)
        else:
            print(f"File not found: {abs_path}")

def main():
    benchmark_file = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark_20250831_2032.json"

    selected_case_file = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark_20250831_2032_selected_300.json"

    # select_sample(benchmark_file, selected_case_file)

    test_case_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/conan_test_cases"
    output_dir = "/Users/liuchengyue/Desktop/BinarySCA Platform/Data/Test_Cases/TPL_Test_Cases/test_cases_selected_300"
    copy_files(selected_case_file, test_case_dir, output_dir)





if __name__ == '__main__':
    main()