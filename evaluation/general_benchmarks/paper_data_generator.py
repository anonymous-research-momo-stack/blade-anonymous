












class PaperDataGenerator():

    def __init__(self,):
        pass

    def generate_data_stats(self):
        """
        生成论文中需要的统计数据，输出latex格式的段落
        所有数字都是变量，需要手动填写
        """
        # 所有变量都需要手动填写
        TOTAL_BINARY_FILES = 3489  # 总的二进制文件数量（去重后）
        TOTAL_REUSE_RELATIONSHIPS = 3000  # 总的复用关系数量 # TODO 待确定最终数字
        TOTAL_TPLS = 1226  # 有测试用例覆盖的TPL数量
        TOTAL_TOPICS = 1931  # Topics种类总数
        TOTAL_CONAN_PROJECTS = 1775  # 从Conan收集的项目总数
        SUCCESSFULLY_COMPILED_PROJECTS = 1085  # 成功编译的项目数

        # 表格中各配置的数据
        GCC_ARM_BINARIES = 1269  # gcc+arm配置的二进制文件数
        GCC_ARM_TPLS = 1220  # gcc+arm配置的TPL数量
        GCC_ARM_REUSES = 1000  # gcc+arm配置的复用关系数 # TODO 待确定最终数字

        CLANG_X86_BINARIES = 1223  # clang+x86_64配置的二进制文件数
        CLANG_X86_TPLS = 1189  # clang+x86_64配置的TPL数量
        CLANG_X86_REUSES = 1000  # clang+x86_64配置的复用关系数

        GCC_X86_BINARIES = 1039  # gcc+x86_64配置的二进制文件数
        GCC_X86_TPLS = 1009  # gcc+x86_64配置的TPL数量
        GCC_X86_REUSES = 1000  # gcc+x86_64配置的复用关系数 # TODO 待确定最终数字

        # 打印LaTeX内容
        print(
            f"""
To evaluate the performance of our tool in binary TPL detection, we constructed a comprehensive and diverse test dataset comprising \\var{{{TOTAL_BINARY_FILES:,}}} binary files and \\var{{{TOTAL_REUSE_RELATIONSHIPS:,}}} reuse relationships of \\var{{{TOTAL_TPLS:,}}} TPLs. 
The dataset covers different compilers, architectures, and optimization levels to assess cross-platform detection capabilities. 
The included TPLs span over \\var{{{TOTAL_TOPICS:,}}} distinct functional categories (as classified by Conan's topic taxonomy), ensuring comprehensive diversity and representativeness across the C/C++ ecosystem.
Specifically, we first collected information on \\var{{{TOTAL_CONAN_PROJECTS:,}}} projects from Conan, a widely-used C/C++ package manager, where these projects serve as prevalent TPLs throughout the C/C++ ecosystem. 
We then established three compilation configurations to assess the tool's cross-compiler and cross-architecture detection capabilities: we used the most common gcc+x86\\_64 as the baseline configuration, and following the controlled variable principle, created a clang+x86\\_64 configuration by varying the compiler and a gcc+arm configuration by varying the target architecture. All configurations employed Release-level compilation (corresponding to O2 and O3 in Conan). 
We subsequently attempted to compile all \\var{{{TOTAL_CONAN_PROJECTS:,}}} projects across the three configurations, successfully compiling \\var{{{SUCCESSFULLY_COMPILED_PROJECTS:,}}} projects. Due to transitive dependencies, the compilation process yielded binary artifacts for \\var{{{TOTAL_TPLS:,}}} distinct TPLs, comprising both the successfully compiled projects and their dependency libraries. 
From these compilation outputs, we systematically extracted binary files by parsing the bin and lib directories across all compilation configurations. After applying hash-based deduplication to remove identical binaries generated across different configurations, we obtained \\var{{{TOTAL_BINARY_FILES:,}}} unique binary files. All binary files were further processed using the strip command to remove symbol tables and debug information, thereby better simulating real-world deployment scenarios where such metadata is typically absent.
Finally, we annotated a total of \\var{{{TOTAL_REUSE_RELATIONSHIPS:,}}} reuse relationships as ground truth by analyzing dependency relationships in Conan-provided receipts and rigorously examining project source directories and key files, including build configuration files (e.g., CMakeLists.txt, Makefiles), header files, documentation files (README, CHANGELOG), and license files. 
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
    def generate_comparison_table(self):
        pass

    def generate_ablation_table(self):
        pass

    def generate_time_breakdown_table(self):
        pass


def main():
    generator = PaperDataGenerator()
    generator.generate_data_stats()
    # generator.generate_comparison_table()
    # generator.generate_ablation_table()
    # generator.generate_time_breakdown_table()

if __name__ == '__main__':
    main()