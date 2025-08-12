import json
import os
from typing import Optional, Dict, Any

from evaluation.general_benchmarks.interface import Benchmark, SimpleEvaluationReport, EvaluationReport


class PaperDataGenerator():

    def __init__(self):
        pass

    def generate_data_stats(self):
        """
        这些数据来源于两个地方：
        1. conan_benchmark_generater.py 的编译结果的统计
        2. benchmark自己的统计
        """
        # 所有变量都需要手动填写
        TOTAL_CONAN_PROJECTS = 1775  # 从Conan收集的项目总数
        SUCCESSFULLY_COMPILED_PROJECTS = 1085  # 成功编译的项目数
        TOTAL_TOPICS = 1931  # Topics种类总数

        TOTAL_BINARY_FILES = 3489  # 总的二进制文件数量（去重后）
        TOTAL_TPLS = 995  # 有测试用例覆盖的TPL数量
        TOTAL_REUSE_RELATIONSHIPS = 3489  # 总的复用关系数量 # TODO 待确定最终数字

        # 表格中各配置的数据
        GCC_X86_BINARIES = 1239  # gcc+x86_64配置的二进制文件数
        GCC_X86_TPLS = 963  # gcc+x86_64配置的TPL数量
        GCC_X86_REUSES = 1239  # gcc+x86_64配置的复用关系数 # TODO 待确定最终数字

        GCC_ARM_BINARIES = 1269  # gcc+arm配置的二进制文件数
        GCC_ARM_TPLS = 842  # gcc+arm配置的TPL数量
        GCC_ARM_REUSES = 1039  # gcc+arm配置的复用关系数 # TODO 待确定最终数字

        CLANG_X86_BINARIES = 1211  # clang+x86_64配置的二进制文件数
        CLANG_X86_TPLS = 944  # clang+x86_64配置的TPL数量
        CLANG_X86_REUSES = 1211  # clang+x86_64配置的复用关系数 # TODO 待确定最终数字

        # 打印LaTeX内容
        print(
            f"""
To evaluate the performance of our tool in binary TPL detection, we constructed a comprehensive and diverse test dataset comprising \\var{{{TOTAL_BINARY_FILES:,}}} binary files and \\var{{{TOTAL_REUSE_RELATIONSHIPS:,}}} reuse relationships of \\var{{{TOTAL_TPLS:,}}} TPLs. 
The dataset covers different compilers, architectures, and optimization levels to assess cross-platform detection capabilities. 
The included TPLs span over \\var{{{TOTAL_TOPICS:,}}} distinct functional categories (as classified by Conan's topic taxonomy), ensuring comprehensive diversity and representativeness across the C/C++ ecosystem.
Specifically, we first collected information on \\var{{{TOTAL_CONAN_PROJECTS:,}}} projects from Conan, a widely-used C/C++ package manager, where these projects serve as prevalent TPLs throughout the C/C++ ecosystem. 
We then established three compilation configurations to assess the tool's cross-compiler and cross-architecture detection capabilities: we used the most common gcc+x86\\_64 as the baseline configuration, and following the controlled variable principle, created a clang+x86\\_64 configuration by varying the compiler and a gcc+arm configuration by varying the target architecture. All configurations employed Release-level compilation (corresponding to O2 and O3 in Conan). 
We attempted to compile all \\var{{{TOTAL_CONAN_PROJECTS:,}}} projects across the three configurations. Due to complex compilation configurations, some projects failed to compile successfully. The compilation process ultimately yielded binary artifacts for \var{{{TOTAL_TPLS:,}}} distinct TPLs, comprising both the successfully compiled projects and their dependency libraries.
From these compilation outputs, we systematically extracted binary files by parsing the bin and lib directories across all compilation configurations. After applying hash-based deduplication to remove identical binaries generated across different configurations, we obtained \\var{{{TOTAL_BINARY_FILES:,}}} unique binary files. All binary files were further processed using the strip command to remove symbol tables and debug information, thereby better simulating real-world deployment scenarios where such metadata is typically absent.
Finally, following previous work \\todo{{[CITE]}}, we annotated a total of \\var{{{TOTAL_REUSE_RELATIONSHIPS:,}}} reuse relationships as ground truth by analyzing dependency relationships in Conan-provided receipts and rigorously examining project source directories and key files, including build configuration files (e.g., CMakeLists.txt, Makefiles), header files, documentation files (README, CHANGELOG), and license files. 
This resulted in the largest dataset in the field of binary-to-source software composition analysis, with test case scales exceeding previous work by more than 20 times, while previous datasets typically contain 100-200 binary files~\\cite{{TODO}}. Table~\\ref{{tab:dataset_distribution}} shows the distribution of binary files across different compilation configurations, demonstrating the balanced coverage of our test dataset.
\\begin{{table}}[htbp]
\\centering
\\caption{{Distribution of Binary Files Across Compilation Configurations}}
\\label{{tab:dataset_distribution}}
\\begin{{tabular}}{{lccc}}
\\toprule
Configuration & Binary Files & TPLs & Reuse Relationships \\\\
\\midrule
gcc+arm & \\var{{{GCC_ARM_BINARIES:,}}} & \\var{{{GCC_ARM_TPLS:,}}} & \\var{{{GCC_ARM_REUSES:,}}} \\\\
clang+x86\\_64 & \\var{{{CLANG_X86_BINARIES:,}}} & \\var{{{CLANG_X86_TPLS:,}}} & \\var{{{CLANG_X86_REUSES:,}}} \\\\
gcc+x86\\_64 & \\var{{{GCC_X86_BINARIES:,}}} & \\var{{{GCC_X86_TPLS:,}}} & \\var{{{GCC_X86_REUSES:,}}} \\\\
\\midrule
Total & \\var{{{TOTAL_BINARY_FILES:,}}} & \\var{{{TOTAL_TPLS:,}}} & \\var{{{TOTAL_REUSE_RELATIONSHIPS:,}}} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}
    """)

    import os
    import json
    from typing import Optional, Dict, Any

    def generate_comparison_table(self, tools_config: Dict[str, Dict[str, Dict[str, str]]]):
        """
        生成对比表格，支持灵活的工具配置。

        Args:
            tools_config: 两层字典结构
            {
                "commercial": {
                    "tool_key": {"path": "文件路径", "display_name": "显示名称"},
                    ...
                },
                "academic": {
                    "tool_key": {"path": "文件路径", "display_name": "显示名称"},
                    ...
                },
                "ours": {
                    "tool_key": {"path": "文件路径", "display_name": "显示名称"},
                    ...
                }
            }
        """

        def load_report_data(file_path: str) -> Optional[Dict[str, Any]]:
            """加载报告数据"""
            if not os.path.exists(file_path):
                return None

            try:
                # 尝试加载为 EvaluationReport 或 SimpleEvaluationReport
                if file_path.endswith('_simple.json'):
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    report = SimpleEvaluationReport.init_from_dict(data)
                else:
                    report = EvaluationReport.load_from_file(file_path)

                return report.research_question_data
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                return None

        def extract_effectiveness_metrics(effectiveness_data) -> Dict[str, str]:
            """提取效果指标并格式化"""
            if effectiveness_data is None:
                return {"recall": "xxx", "precision": "xxx", "f1_score": "xxx"}

            recall = f"{effectiveness_data.recall:.1f}" if effectiveness_data.recall is not None else "xxx"
            precision = f"{effectiveness_data.precision:.1f}" if effectiveness_data.precision is not None else "xxx"
            f1_score = f"{effectiveness_data.f1_score:.1f}" if effectiveness_data.f1_score is not None else "xxx"

            return {"recall": recall, "precision": precision, "f1_score": f1_score}

        def generate_row_data(tool_name: str, research_data, tool_type: str, is_first_ours: bool = False) -> str:
            """生成单行数据"""
            if research_data is None:
                # 没有数据时，所有指标都显示xxx
                row_data = ["xxx"] * 12  # 4个配置 * 3个指标
            else:
                # 提取四种配置的数据
                overall = extract_effectiveness_metrics(research_data.effectiveness)
                gcc_x86 = extract_effectiveness_metrics(research_data.gcc_x86_effectiveness)
                gcc_arm = extract_effectiveness_metrics(research_data.gcc_arm_effectiveness)
                clang_x86_64 = extract_effectiveness_metrics(research_data.clang_x86_64_effectiveness)

                row_data = [
                    overall["recall"], overall["precision"], overall["f1_score"],
                    gcc_x86["recall"], gcc_x86["precision"], gcc_x86["f1_score"],
                    gcc_arm["recall"], gcc_arm["precision"], gcc_arm["f1_score"],
                    clang_x86_64["recall"], clang_x86_64["precision"], clang_x86_64["f1_score"]
                ]

            # 如果是我们的工具且是第一个，加粗显示
            if tool_type == "ours" and is_first_ours:
                row_data = [f"\\textbf{{{value}}}" if value != "xxx" else value for value in row_data]

            # 格式化为LaTeX行
            data_str = " & ".join(row_data)
            return f"        {tool_name} & {data_str} \\\\"

        # 按指定顺序处理工具类型
        type_order = ["commercial", "academic", "ours"]
        all_rows = []

        for tool_type in type_order:
            if tool_type not in tools_config:
                continue

            type_rows = []
            is_first_ours = True  # 标记是否为该类型的第一个工具

            for tool_key, tool_info in tools_config[tool_type].items():
                file_path = tool_info["path"]
                display_name = tool_info["display_name"]

                research_data = load_report_data(file_path)
                row = generate_row_data(
                    display_name,
                    research_data,
                    tool_type,
                    is_first_ours and tool_type == "ours"
                )
                type_rows.append(row)

                if tool_type == "ours":
                    is_first_ours = False

            if type_rows:
                all_rows.extend(type_rows)
                # 在类型之间添加分隔线（除了最后一个类型）
                if tool_type != type_order[-1] and tool_type != "ours":
                    all_rows.append("            \\hline")

        # 在我们的工具前添加分隔线
        if "ours" in tools_config and tools_config["ours"]:
            # 找到我们工具开始的位置，在前面插入分隔线
            ours_start_idx = len(all_rows)
            for i, row in enumerate(all_rows):
                if "\\textbf{Ours-" in row:
                    ours_start_idx = i
                    break
            if ours_start_idx < len(all_rows):
                all_rows.insert(ours_start_idx, "            \\hline")

            # 生成完整的LaTeX表格
            latex_table = f"""
\\begin{{table}}[t]
\\captionsetup{{skip=1pt, belowskip=7pt}}
\\caption{{SCA Result Comparison on Different Architectures}}
\\label{{tab:tpl_detection_comparison}}
\\scriptsize  % 使用更小的字体
\\setlength{{\\tabcolsep}}{{3pt}}  % 减小列间距
\\begin{{tabularx}}{{\\linewidth}}{{>{{\\centering\\arraybackslash}}p{{2.0cm}}|YYY|YYY|YYY|YYY}}
    \\toprule
    & \\multicolumn{{3}}{{c|}}{{\\textbf{{Overall}}}} & \\multicolumn{{3}}{{c|}}{{\\textbf{{GCC x86}}}} & \\multicolumn{{3}}{{c|}}{{\\textbf{{GCC ARM}}}} & \\multicolumn{{3}}{{c}}{{\\textbf{{Clang x86\\_64}}}} \\\\  
    \\cmidrule(lr){{2-4}} \\cmidrule(lr){{5-7}} \\cmidrule(lr){{8-10}} \\cmidrule(lr){{11-13}}
    \\textbf{{Tool}} & R & P & F1 & R & P & F1 & R & P & F1 & R & P & F1 \\\\
    \\midrule
{chr(10).join(all_rows)}
    \\bottomrule
\\end{{tabularx}}
\\vspace{{1mm}}
\\scriptsize
\\textbf{{Note:}} R = Recall (\\%), P = Precision (\\%), F1 = F1-Score (\\%); G4 = OpenAI GPT-4.1, G4M = OpenAI GPT-4.1-mini, S4 = Anthropic Sonnet-4.0, GOS = OpenAI GPT-OSS:20b, QW3 = Qwen3:14b.
\\end{{table}}
"""

        print("Generated LaTeX Table:")
        print("=" * 80)
        print(latex_table)
        print("=" * 80)

        return latex_table

    def generate_ablation_table(self):
        pass

    def generate_time_breakdown_table(self):
        pass


def print_dataset_preview():
    # 打印数据预览
    benchmark_dir = '/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta'
    benchmark_name = 'conan_library_benchmark_20250806_1524.json'
    benchmark_path = f'{benchmark_dir}/{benchmark_name}'
    benchmark = Benchmark.load_from_json_file(benchmark_path)
    benchmark.stat()

    # 打印数据集预览
    generator = PaperDataGenerator()
    generator.generate_data_stats()
    # generator.generate_comparison_table()
    # generator.generate_ablation_table()
    # generator.generate_time_breakdown_table()


def print_RQ1_data():
    generator = PaperDataGenerator()
    tools_config = {
        "commercial": {
            "scantist": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/scantist/291-75403-xd70-无agent-扫描报告-2025-08-06T09_36_22+08_00/result_converted_reanalyzed_simple.json",
                "display_name": "CT1"},
            "cybellum": {
                "path": "",
                "display_name": "CT2"},
            "blackduck": {
                "path": "",
                "display_name": "CT3"}
        },
        "academic": {
            "BAT": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/bat/raw_result_converted_reanalyzed_simple.json",
                "display_name": "BAT"},
            "OssPolice": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/osspolice/raw_result_converted_reanalyzed_simple.json",
                "display_name": "OssPolice"},
            "B2SFinder": {
                "path": "",
                "display_name": "B2SFinder"},
            "LibAM": {
                "path": "",
                "display_name": "LibAM"},
            "binary_ai": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/binary_ai/evaluation_report_2025-07-30-12-54-29_converted_reanalyzed_simple.json",
                "display_name": "BinaryAI"},
        },
        "ours": {
            "our-OpenAI-GPT-4.1": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours_102_mini_all_0831/evaluation_report_reanalyzed_simple.json",
                "display_name": "\\textbf{Blade-G4.1}"},
            "our-OpenAI-GPT-4.1-mini": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours_105_0806/evaluation_report_reanalyzed_simple.json",
                "display_name": "\\textbf{Blade-G4.1m}"},
            "our-Anthropic-Sonnet-4.0": {
                "path": "",
                "display_name": "\\textbf{Blade-S4}"},
            "our-Ollama-gpt-oss-20b": {
                "path": "",
                "display_name": "Blade-GOS"},
            "our-Ollama-qwen3-14b": {
                "path": "",
                "display_name": "Blade-QW3"},
        }
    }
    generator.generate_comparison_table(tools_config=tools_config)

    pass


def main():
    print_RQ1_data()


if __name__ == '__main__':
    main()
