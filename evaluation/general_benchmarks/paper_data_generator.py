import json
import os
from typing import Optional, Dict, Any

from pandas.core.computation.expr import intersection

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

            recall = f"{effectiveness_data.recall:.2f}" if effectiveness_data.recall is not None else "xxx"
            precision = f"{effectiveness_data.precision:.2f}" if effectiveness_data.precision is not None else "xxx"
            f1_score = f"{effectiveness_data.f1_score:.2f}" if effectiveness_data.f1_score is not None else "xxx"

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
            "blackduck": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/blackduck/result_converted_reanalyzed_simple.json",
                "display_name": "CT2"}
        },
        "academic": {
            "BAT": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/bat/raw_result_converted_reanalyzed_simple.json",
                "display_name": "BAT"},
            "OssPolice": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/osspolice/raw_result_converted_reanalyzed_simple.json",
                "display_name": "OssPolice"},
            "B2SFinder": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/b2sfinder/result_converted_reanalyzed_simple.json",
                "display_name": "B2SFinder"},
            "binary_ai": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/binary_ai/evaluation_report_2025-07-30-12-54-29_converted_reanalyzed_simple.json",
                "display_name": "BinaryAI"},
        },
        "ours": {
            "our-OpenAI-GPT-5": {
                "path": "",
                "display_name": "\\textbf{Blade-G5}"},
            "our-OpenAI-GPT-5-mini": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_5_mini/evaluation_report_reanalyzed_simple.json",
                "display_name": "\\textbf{Blade-G5m}"},
            "our-OpenAI-GPT-5-nano": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_5_nano/evaluation_report_reanalyzed_simple.json",
                "display_name": "\\textbf{Blade-G5n}"},
            "our-Anthropic-Sonnet-4.0": {
                "path": "",
                "display_name": "\\textbf{Blade-S4}"},
            "our-Ollama-gpt-oss-20b": {
                "path": "",
                "display_name": "Blade-GOS"},
            "our-Ollama-qwen3-14b": {
                "path": "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/qwen3/evaluation_report_reanalyzed_simple.json",
                "display_name": "Blade-QW3"},
        }
    }
    generator.generate_comparison_table(tools_config=tools_config)

    # 进一步的结果分析
    all_baseline_paths = []
    for type, baselines in tools_config.items():
        if type == "ours":
            continue
        for basline_name, baseline_info in baselines.items():
            if baseline_info["path"]:
                all_baseline_paths.append(baseline_info["path"])

    analyze_RQ1_results(
        benchmark_meta="/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/evaluation/general_benchmarks/benchmark_meta/conan_library_benchmark_20250806_1524.json",
        our_result="/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_4_1_mini/ours_105_0806/evaluation_report_reanalyzed_simple.json",
        baseline_results=all_baseline_paths
    )
    pass

def analyze_RQ1_results(benchmark_meta, our_result, baseline_results):
    benchmark = Benchmark.load_from_json_file(benchmark_meta)
    test_case_dict = {case.test_binary.sha256: case for case in benchmark.test_cases}

    def load_result(file_path)-> SimpleEvaluationReport:
        with open(file_path, 'r') as f:
            data = json.load(f)
        report = SimpleEvaluationReport.init_from_dict(data)
        return report

    our_result = load_result(our_result)
    our_result_check = {check.binary_hash: (check.hs_fn, check.hs_fp) for check in our_result.evaluation_results_check}
    print(baseline_results)
    baseline_results = [load_result(path) for path in baseline_results]

    advantage_analysis(baseline_results, benchmark, our_result_check, test_case_dict)
    failure_analysis(benchmark, our_result)

def failure_analysis(benchmark, our_result:SimpleEvaluationReport):

    print(f"==== Failure Analysis ====")
    fn_cases = set()
    fp_cases = set()
    for check in our_result.evaluation_results_check:
        if check.hs_fn:
            fn_cases.add(check.binary_hash)
        if check.hs_fp:
            fp_cases.add(check.binary_hash)

    intersection = fn_cases.intersection(fp_cases)
    print(f"fn_cases数量: {len(fn_cases)}, fp_cases数量: {len(fp_cases)}, fn和fp的交集数量: {len(intersection)}")
    print(fn_cases)

def advantage_analysis(baseline_results, benchmark, our_result_check, test_case_dict):
    # 先生成全部的baseline工具的漏报检查
    baseline_has_fn_cases = {}
    baseline_has_fp_cases = {}
    for baseline_result in baseline_results:
        print(len(baseline_result.evaluation_results_check))
        for result_check in baseline_result.evaluation_results_check:
            # fn
            if result_check.binary_hash not in baseline_has_fn_cases:
                baseline_has_fn_cases[result_check.binary_hash] = []
            baseline_has_fn_cases[result_check.binary_hash].append(result_check.hs_fn)

            # fp
            if result_check.binary_hash not in baseline_has_fp_cases:
                baseline_has_fp_cases[result_check.binary_hash] = []
            baseline_has_fp_cases[result_check.binary_hash].append(result_check.hs_fp)
    # 找到都漏报的结果
    all_baseline_fn_cases = []
    for case_hash, hs_fn_checks in baseline_has_fn_cases.items():
        # 我们的结果
        if len([check for check in hs_fn_checks if check]) >= 6 and not our_result_check[case_hash][0]:
            all_baseline_fn_cases.append(case_hash)
    print(f"全部baseline工具都漏报, 但是我们正常检测的的cases数量: {len(all_baseline_fn_cases)}")
    # 分类统计
    mini_size_cases = []
    TPL_names = set()
    for case_hash in all_baseline_fn_cases:
        case = test_case_dict.get(case_hash, None)
        # print(case.test_binary.file_size_kb)
        if case.test_binary.file_size_kb <= 100:
            mini_size_cases.append(case_hash)
        TPL_names.add(case.reused_libraries[0].name)
    # benchmark 小文件数量
    print(
        f"数据集, 小文件(<=100KB)数量: {len([case for case in benchmark.test_cases if case.test_binary.file_size_kb <= 100])}，占比: {len([case for case in benchmark.test_cases if case.test_binary.file_size_kb <= 100]) / len(benchmark.test_cases):.2%}")
    # benchmark 平均文件大小
    print(
        f"数据集, 平均文件大小: {sum([case.test_binary.file_size_kb for case in benchmark.test_cases]) / len(benchmark.test_cases):.2f} KB")
    # 小文件数量, 占比
    print(
        f"全部baseline工具都漏报的cases中, 小文件(<=100KB)数量: {len(mini_size_cases)}，占比: {len(mini_size_cases) / len(all_baseline_fn_cases):.2%}")
    print(f"全部baseline工具都漏报的cases中, 涉及的TPL数量: {len(TPL_names)}, preview: {list(TPL_names)[:10]}")
    print(list(TPL_names))
    print(f"---" * 20)
    # 找到都误报的结果
    all_baseline_fp_cases = []
    for case_hash, hs_fp_checks in baseline_has_fp_cases.items():
        # 至少两个误报，hs_fp_checks 里面至少两个True
        if len([check for check in hs_fp_checks if check]) >= 3 and not our_result_check[case_hash][1]:
            all_baseline_fp_cases.append(case_hash)
    print(f"全部baseline工具都误报的cases数量: {len(all_baseline_fp_cases)}")
    # 分类统计
    TPL_names = set()
    for case_hash in all_baseline_fp_cases:
        case = test_case_dict.get(case_hash, None)
        TPL_names.add(case.reused_libraries[0].name)
    print(f"全部baseline工具都误报的cases中, 涉及的TPL数量: {len(TPL_names)}, preview: {list(TPL_names)[:10]}")
    print(list(TPL_names))
    """
        # C/C++库分类列表
    
        ## 1. 超高频依赖库（28个，14.3%）
        ```
        zlib, sqlite3, protobuf, flatbuffers, libuv, mbedtls, libsodium,
        bzip2, lz4, zstd, pcre, pcre2, icu, libiconv, utf8proc,
        base64, cjson, parson, libarchive, minizip, xz_utils, libgettext,
        libunistring, date, libdb, jemalloc, bdwgc, re2
        ```
    
        ## 2. 标准算法实现库（38个，19.4%）
        ```
        lzo, easylzma, fpzip, lerc, crunch, qr - code - generator, poly2tri,
        rectanglebinpack, tiny - aes - c, libhydrogen, s2n, gnutls, krb5,
        opus, flac, libmp3lame, alac, dav1d, libaom - av1, libsvtav1,
        vvenc, libraw, libtiff, libwebp, freeimage, exiv2, mpg123,
        drwav, libmad, libmodplug, libsndfile, opusfile, pdfium,
        tesseract, zbar, zint, hunspell, lightpcapng
        ```
    
        ## 3. 通用工具框架库（37个，18.9%）
        ```
        poco, cpprestsdk, grpc, fast - dds, benchmark, cppbenchmark,
        spdlog, g3log, libassert, gperftools, onetbb, llvm - openmp,
        argtable2, argtable3, json - schema - validator, onnx, openvino,
        lightgbm, itk, openblas, xnnpack, dpp, tgbot, wt, civetweb,
        cppserver, angelscript, luajit, jerryscript, duktape, wasmedge,
        rttr, lief, capstone, doxygen, jinja2cpp, tidy - html5
        ```
    
        ## 4. 底层系统库（29个，14.8%）
        ```
        pixman, editline, wayland, libdwarf, libelfin, libdisasm,
        tcl, flex, bison, yasm, nasm, gn, b2, scdoc,
        xorg - makedepend, eudev, gobject - introspection, glibmm, gdk - pixbuf,
        libpcap, libnetfilter_conntrack, rsync, libsafec, libucl,
        cfgfile, libsersi, libtasn1, tree - sitter - cpp, lemon
        ```
    
        ## 5. 网络协议栈库（15个，7.7%）
        ```
        nghttp3, libnghttp2, llhttp, http_parser, libssh2, cnats,
        hiredis, cassandra - cpp - driver, mariadb - connector - c, libpq,
        orcania, libgit2, keychain, ohnet, nmea
        ```
    
        ## 6. 其他特定领域库（49个，25.0%）
        ```
        ccfits, glbinding, dispenso, openvino, roaring, lightpcapng,
        laszip, coin - utils, tinyobjloader, openddl - parser, libsvm,
        libmeshb, libdrawille, litehtml, edyn, spirv - cross,
        mbits - lngs, sqlcipher, eiquadprog, rocksdb, sbp,
        libpfm4, dfp, open - dis - cpp, libspatialite, nodesoup, gklib,
        muparser, proj, metis, nmea, aaf, cnpy, opene57,
        podofo, implot, spirv - tools, libsquish, libharu, uni - algo,
        mpir, fastgltf, qdbm, bgfx, shapelib, gdal, rply,
        imguizmo, cgltf, 以及其他专业领域库
        ```
        """


def generate_ablation_table(baseline_name,
                            baseline_data,
                            ablation_data,
                            table_title="Ablation Study Results of TPL Detection"):
    """
    生成消融研究的LaTeX表格

    Args:
        baseline_data: 基准模型数据字典
        ablation_data: 消融实验数据字典
        table_title: 表格标题

    Returns:
        完整的LaTeX表格代码字符串
    """

    # 映射消融实验键名到表格显示名称
    row_mapping = {
        "wo_agent_analysis": "w/o r/v \\& n = 5",
        "wo_agent_analysis_top_1": "w/o r/v \\& n = 1",
        "wo_agent_analysis_top_2": "w/o r/v \\& n = 2",
        "wo_agent_analysis_top_3": "w/o r/v \\& n = 3",
        "wo_agent_tpl_analysis": "w/o r",
        "wo_validation_step_1": "w/o v step 1",
        "wo_validation_step_2": "w/o v step 2",
        "wo_validation_step_1_and_2": "w/o v step 1\\&2"
    }

    # 定义分组，用于添加 \midrule
    groups = [
        ["wo_agent_analysis", "wo_agent_analysis_top_1", "wo_agent_analysis_top_2", "wo_agent_analysis_top_3"],
        ["wo_agent_tpl_analysis"],
        ["wo_validation_step_1", "wo_validation_step_2", "wo_validation_step_1_and_2"]
    ]

    def format_number(num):
        """格式化数字，数字本身不加逗号，让siunitx自动处理"""
        return str(num)

    def format_diff_number(num):
        """格式化差值数字，手动添加逗号用于括号内显示"""
        if isinstance(num, int) and abs(num) >= 1000:
            return f"{num:,}"
        return str(num)

    def calculate_diff_and_color(baseline_val, ablation_val, metric_type):
        """计算差值并确定颜色"""
        diff = ablation_val - baseline_val

        # 修复浮点数精度问题
        if metric_type in ['f1_score', 'recall', 'precision']:
            diff = round(diff, 2)  # 保留两位小数

        # 确定是否为改善
        if metric_type in ['f1_score', 'recall', 'precision', 'tp_count']:
            is_better = diff > 0
        elif metric_type in ['fp_count', 'fn_count']:
            is_better = diff < 0
        else:
            is_better = False

        # 格式化差值
        if diff > 0:
            if metric_type in ['f1_score', 'recall', 'precision']:
                diff_str = f"+{diff:.2f}"
            else:
                diff_str = f"+{format_diff_number(int(diff))}"
        elif diff < 0:
            if metric_type in ['f1_score', 'recall', 'precision']:
                diff_str = f"{diff:.2f}"
            else:
                diff_str = format_diff_number(int(diff))
        else:
            diff_str = "0"

        # 选择颜色
        if diff == 0:
            return diff_str
        elif is_better:
            return f"\\textcolor{{OliveGreen}}{{{diff_str}}}"
        else:
            return f"\\textcolor{{red}}{{{diff_str}}}"

    # 开始构建LaTeX表格 - 关键修改：移除group-separator参数
    latex_code = f"""\\begin{{table*}}[htbp]
   \\centering
   \\captionsetup{{skip=0pt, belowskip=5pt}}
   \\caption{{{table_title}}}
   \\label{{tab:ablation_study}}
   \\footnotesize
\\begin{{tabular*}}{{\\textwidth}}{{@{{\\extracolsep{{\\fill}}}}l
               S[table-format=2.2]@{{\\hspace{{0.1em}}}}l
               S[table-format=2.2]@{{\\hspace{{0.1em}}}}l
               S[table-format=2.2]@{{\\hspace{{0.1em}}}}l
               S[table-format=4.0,group-separator={{,}}]@{{\\hspace{{0.1em}}}}l
               S[table-format=5.0,group-separator={{,}}]@{{\\hspace{{0.1em}}}}l
               S[table-format=4.0,group-separator={{,}}]@{{\\hspace{{0.1em}}}}l}}
       \\toprule
       \\textbf{{Setting}} & \\multicolumn{{2}}{{l}}{{\\textbf{{F1 Score (\\%)}}}} & \\multicolumn{{2}}{{l}}{{\\textbf{{Recall (\\%)}}}} & \\multicolumn{{2}}{{l}}{{\\textbf{{Precision (\\%)}}}} & \\multicolumn{{2}}{{l}}{{\\textbf{{\\#TP}}}} & \\multicolumn{{2}}{{l}}{{\\textbf{{\\#FP}}}} & \\multicolumn{{2}}{{l}}{{\\textbf{{\\#FN}}}} \\\\
       \\midrule

       \\textbf{{{baseline_name}}} & \\textbf{{{baseline_data['f1_score']:.2f}}} & & \\textbf{{{baseline_data['recall']:.2f}}} & & \\textbf{{{baseline_data['precision']:.2f}}} & & \\textbf{{{format_number(baseline_data['tp_count'])}}} & & \\textbf{{{format_number(baseline_data['fp_count'])}}} & & \\textbf{{{format_number(baseline_data['fn_count'])}}} & \\\\

       \\midrule
       """

    # 添加消融实验行
    current_group = 0
    for i, (key, display_name) in enumerate(row_mapping.items()):
        if key in ablation_data:
            data = ablation_data[key]

            # 计算差值和颜色
            f1_diff = calculate_diff_and_color(baseline_data['f1_score'], data['f1_score'], 'f1_score')
            recall_diff = calculate_diff_and_color(baseline_data['recall'], data['recall'], 'recall')
            precision_diff = calculate_diff_and_color(baseline_data['precision'], data['precision'], 'precision')
            tp_diff = calculate_diff_and_color(baseline_data['tp_count'], data['tp_count'], 'tp_count')
            fp_diff = calculate_diff_and_color(baseline_data['fp_count'], data['fp_count'], 'fp_count')
            fn_diff = calculate_diff_and_color(baseline_data['fn_count'], data['fn_count'], 'fn_count')

            # 添加行 - 数字本身用format_number(不加逗号)，差值用计算出的带逗号的diff字符串
            latex_code += f"""        {display_name} & {data['f1_score']:.2f} & ({f1_diff}) & {data['recall']:.2f} & ({recall_diff}) & {data['precision']:.2f} & ({precision_diff}) & {format_number(data['tp_count'])} & ({tp_diff}) & {format_number(data['fp_count'])} & ({fp_diff}) & {format_number(data['fn_count'])} & ({fn_diff}) \\\\"""

            # 检查是否需要添加分组分隔符
            if current_group < len(groups):
                if key == groups[current_group][-1] and current_group < len(groups) - 1:
                    latex_code += """

       \\midrule
       """
                    current_group += 1
                else:
                    latex_code += "\n"

    # 表格结尾
    latex_code += """        
       \\bottomrule
   \\end{tabular*}
   \\vspace{1mm}
   \\footnotesize
   r = Reasoning Agent, v = Validation Agent, n = feature matching method set to take top n results, step 1 = rationality validation, step 2 = redundancy elimination and conflict resolution. Changes relative to full model are shown in parentheses: \\textcolor{OliveGreen}{OliveGreen} indicates better performance, \\textcolor{red}{red} indicates worse performance.
\\end{table*}"""

    return latex_code



def print_RQ2_data():
    baseline_name = "Blade-G4.1m"
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_4_1_mini/ours_105_0806/evaluation_report_reanalyzed_simple.json"
    with open(result_path, 'r') as f:
        data = json.load(f)
    baseline_data = data['research_question_data']['effectiveness']
    ablation_data = data['research_question_data']['effectiveness_ablation_study']
    table_latex = generate_ablation_table(baseline_name,baseline_data, ablation_data)
    print(table_latex)
    pass


import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Wedge
import seaborn as sns


def plot_performance_breakdown(duration_breakdown, save_files=True, filename='performance_breakdown'):
    """
    绘制性能分析的双层环形图

    Parameters:
    duration_breakdown (dict): 包含各个步骤耗时的字典
    save_files (bool): 是否自动保存文件
    filename (str): 保存文件的名称前缀
    """

    # 设置图形风格
    plt.style.use('seaborn-v0_8-whitegrid')
    sns.set_palette("husl")

    # 创建子图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('Performance Analysis Breakdown', fontsize=16, fontweight='bold', y=0.95)

    # 定义颜色方案 - 使用学术论文友好的配色
    colors_level1 = ['#3498DB', '#E74C3C', '#F39C12', '#95A5A6']  # 蓝、红、橙、灰
    colors_level2 = ['#3498DB', '#E74C3C', '#2ECC71', '#E67E22', '#F1C40F', '#9B59B6']  # 更丰富的配色

    # ===== 第一个图：第一层分解 =====
    level1_data = {
        'file_preparation': duration_breakdown['file_preparation'],
        'feature_matching': duration_breakdown['feature_matching'],
        'agent_analysis': duration_breakdown['agent_analysis'],
    }

    # 计算其他步骤的总和
    other_steps = 100.0 - sum(level1_data.values())
    if other_steps > 0:
        level1_data['others'] = other_steps

    # 准备数据
    labels1 = list(level1_data.keys())
    sizes1 = list(level1_data.values())

    # 格式化标签，显示百分比
    labels1_formatted = [f'{label.replace("_", " ").title()}\n({size:.1f}%)'
                         for label, size in zip(labels1, sizes1)]

    # 绘制第一个环形图 - 调整环的宽度
    wedges1, texts1, autotexts1 = ax1.pie(sizes1, labels=labels1_formatted, autopct='',
                                          colors=colors_level1[:len(sizes1)], startangle=90,
                                          pctdistance=0.85, wedgeprops=dict(width=0.35, edgecolor='white', linewidth=3))

    # 添加中心圆 - 调整大小
    centre_circle1 = plt.Circle((0, 0), 0.65, fc='white', edgecolor='lightgray', linewidth=2)
    ax1.add_artist(centre_circle1)

    # 设置标题和样式
    ax1.set_title('Level 1: Main Components', fontsize=14, fontweight='bold', pad=20)
    ax1.axis('equal')

    # 美化文本 - 调整字体大小
    for text in texts1:
        text.set_fontsize(12)
        text.set_fontweight('bold')
        text.set_color('black')

    # ===== 第二个图：第二层详细分解 =====
    level2_data = {
        'file_preparation': duration_breakdown['file_preparation'],
        'feature_matching': duration_breakdown['feature_matching'],
        '_bin_info_finder': duration_breakdown['_bin_info_finder'],
        '_tpl_analyzer': duration_breakdown['_tpl_analyzer'],
        '__validation_step_1': duration_breakdown['__validation_step_1'],
        '__validation_step_2': duration_breakdown['__validation_step_2']
    }
    for k,v in duration_breakdown.items():
        print(k, v)

    for k,v in level2_data.items():
        print(f"{k}: {v}%")

    # 计算其他步骤
    other_steps_2 = 100.0 - sum(level2_data.values())
    if other_steps_2 > 0:
        level2_data['others'] = other_steps_2

    # 准备数据
    labels2 = list(level2_data.keys())
    sizes2 = list(level2_data.values())

    # 格式化标签
    label_mapping = {
        'file_preparation': 'File Preparation',
        'feature_matching': 'Feature Matching',
        '_bin_info_finder': 'Binary Info Finder',
        '_tpl_analyzer': 'Template Analyzer',
        '__validation_step_1': 'Validation Step 1',
        '__validation_step_2': 'Validation Step 2',
        'others': 'Others'
    }

    labels2_formatted = [f'{label_mapping.get(label, label.replace("_", " ").title())}\n({size:.1f}%)'
                         for label, size in zip(labels2, sizes2)]

    # 绘制第二个环形图 - 调整环的宽度
    wedges2, texts2, autotexts2 = ax2.pie(sizes2, labels=labels2_formatted, autopct='',
                                          colors=colors_level2[:len(sizes2)], startangle=90,
                                          pctdistance=0.85, wedgeprops=dict(width=0.35, edgecolor='white', linewidth=3))

    # 添加中心圆 - 调整大小
    centre_circle2 = plt.Circle((0, 0), 0.65, fc='white', edgecolor='lightgray', linewidth=2)
    ax2.add_artist(centre_circle2)

    # 设置标题和样式
    ax2.set_title('Level 2: Detailed Breakdown', fontsize=14, fontweight='bold', pad=20)
    ax2.axis('equal')

    # 美化文本 - 调整字体大小
    for text in texts2:
        text.set_fontsize(11)
        text.set_fontweight('bold')
        text.set_color('black')

    # 调整布局
    plt.tight_layout()

    # 自动保存文件（如果需要）
    if save_files:
        save_charts(fig, filename)

    return fig


# 如果需要单独的函数来保存不同格式
def save_charts(fig, filename='performance_breakdown'):
    """
    保存图表为多种适合学术论文的格式
    """
    # PNG格式 - 高分辨率
    fig.savefig(f'{filename}.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')

    # PDF格式 - 矢量图，适合论文
    fig.savefig(f'{filename}.pdf', bbox_inches='tight',
                facecolor='white', edgecolor='none')

    # SVG格式 - 矢量图，可编辑
    fig.savefig(f'{filename}.svg', bbox_inches='tight',
                facecolor='white', edgecolor='none')

    print(f"Charts saved as {filename}.png, {filename}.pdf, and {filename}.svg")

def print_RQ3_data():
    """
    效率和成本
    效率画一个breakdown的饼图

    成本，主要是token数量的breakdown

    :return:
    """
    baseline_name = "Blade-G4.1m"
    result_path = "/Users/liuchengyue/Desktop/BinarySCA Platform/Code/sca_agents/bsca-expert-agent-api/tmp/evaluation_reports/Conan/ours/gpt_4_1_mini/ours_105_0806/evaluation_report_reanalyzed_simple.json"
    with open(result_path, 'r') as f:
        data = json.load(f)
    duration_breakdown = data['research_question_data']['efficiency']['duration_breakdown']

    # 时间breakdown
    fig = plot_performance_breakdown(duration_breakdown)

    # 保存图片（适合论文使用的高质量格式）
    # plt.savefig('performance_breakdown.png', dpi=300, bbox_inches='tight',
    #             facecolor='white', edgecolor='none')
    # plt.savefig('performance_breakdown.pdf', bbox_inches='tight',
    #             facecolor='white', edgecolor='none')

    plt.show()


    # 成本分析，这里先想想怎么写吧。
    """
    平均每个二进制文件的成本为XX tokens，约合XX美元。
    """
    cost = data['research_question_data']['cost']
    for key, value in cost.items():
        print(f"{key}: {value}")


def main():
    print_RQ1_data()
    # print_RQ2_data()
    # print_RQ3_data()



if __name__ == '__main__':
    main()
