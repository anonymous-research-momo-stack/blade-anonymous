from typing import List, Dict

from agno.run.response import RunResponse
from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

from ...config import settings
from ...interface import TargetBinary, Library
from .response_models import TPLAnalysisResult, SoftwareContext
from .model_factory import create_model
from agno.tools.duckduckgo import DuckDuckGoTools


class TPLAnalyzer:
    def __init__(self,
                 knowledge_json_path: str = None,
                 enable_web_search: bool = True,
                 enable_knowledge_base: bool = True,
                 report_custom_components: bool = False,



                 # Prompt显示限制参数
                 max_display_copyright: int = 10,  # Prompt中显示的版权信息数量
                 max_display_paths: int = 8,  # Prompt中显示的路径数量
                 max_display_function_prefixes: int = 10,  # Prompt中显示的函数前缀数量
                 max_display_logs: int = 8,  # Prompt中显示的日志消息数量
                 max_display_versions: int = 5,  # Prompt中显示的版本信息数量
                 max_display_components: int = 5,  # Prompt中显示的组件数量
                 max_matches_per_component: int = 3,  # 每个组件显示的匹配示例数量
                 ):



        # Prompt显示参数配置
        self.max_display_copyright = max_display_copyright  # 版权信息显示上限
        self.max_display_paths = max_display_paths  # 路径信息显示上限
        self.max_display_function_prefixes = max_display_function_prefixes  # 函数前缀显示上限
        self.max_display_logs = max_display_logs  # 日志消息显示上限
        self.max_display_versions = max_display_versions  # 版本信息显示上限
        self.max_display_components = max_display_components  # 组件匹配显示上限
        self.max_matches_per_component = max_matches_per_component  # 每个组件的匹配示例数量

        # Build tools list
        tools = []
        if enable_web_search:
            tools.append(DuckDuckGoTools())

        # Build knowledge base
        knowledge = None
        if enable_knowledge_base:
            if knowledge_json_path is None:
                raise ValueError("knowledge_json_path is required when enable_knowledge_base=True")

            knowledge = JSONKnowledgeBase(
                path=knowledge_json_path,
                vector_db=PgVector(
                    table_name="tpl_analysis_documents",
                    db_url=settings.KNOWLEDGE_DATABASE_URL,
                    search_type=SearchType.hybrid
                ),
            )

        # 核心指令系统 - 修改关键部分
        instructions = [
            "You are an expert binary composition analyst specializing in library source code identification.",
            "",
            "WORKFLOW CONTEXT:",
            "This is STEP 2 of a 3-step binary composition analysis workflow:",
            "• STEP 1 (completed): Binary identity analysis provided preliminary identification",
            "• STEP 2 (your task): Identify ALL libraries whose source code is present in this binary",
            "• STEP 3 (next): Expert validation will verify and refine your findings",
            "",
            "CORE MISSION: Identify libraries whose SOURCE CODE is compiled into this binary file",
            "",
            "CRITICAL TASK DEFINITION:",
            "✓ IDENTIFY: Libraries whose source code is compiled/linked into this binary",
            "✗ NOT: Libraries that this binary calls as external dependencies",
            "✗ NOT: Libraries that this binary may use but are not compiled in",
            "✗ NOT: Similar-named libraries that might share function names",
            "",
            "KEY DISTINCTION:",
            "- 'Source code compiled in' = actual code inclusion during build process",
            "- 'External dependency' = runtime library loading (not your concern)",
            "- 'API similarity' = shared function names (often false positive)",
            "",
            "EVIDENCE VALIDATION APPROACH:",
            "- Cross-validate preliminary identification with string and symbol evidence",
            "- If evidence contradicts preliminary identification, trust the evidence",
            "- Symbol patterns (especially exported symbols) are highly reliable indicators",
            "- Exported symbols reveal the binary's true identity and purpose",
            "",
            "PRIORITY SYSTEM:",
            "1. SYMBOL EVIDENCE: Exported/imported symbol patterns (highest reliability)",
            "2. STRING EVIDENCE: Copyright, paths, function names, component matches",
            "3. PRELIMINARY IDENTIFICATION: From Step 1 (validate, don't assume)",
            "",
            "LIBRARY CONSOLIDATION RULES:",
            "- Report each INDEPENDENT PROJECT only once",
            "- DO NOT separate libraries into sub-components",
            "- Example: Report 'OpenSSL' (not 'libcrypto' + 'libssl' separately)",
            "- Example: Report 'zlib' (not 'inflate' + 'deflate' functions separately)",
            "",
            "CRITICAL EXAMPLES:",
            "✅ CORRECT: Binary 'openssl' → Report 'OpenSSL' (primary source)",
            "✅ CORRECT: Binary 'libssl.a' → Report 'OpenSSL' (source project)",
            "✅ CORRECT: Binary with 'ao_plugin_*' symbols → Report 'libao' (trust symbols over filename)",
            "❌ WRONG: Report both 'OpenSSL' and 'BoringSSL' (competing implementations)",
            "❌ WRONG: Report 'libcrypto' separately from 'OpenSSL' (same project)",
            "",
            "EVIDENCE ANALYSIS:",
            "- STRONG: Copyright/license statements, version strings, project URLs, unique symbol patterns",
            "- MEDIUM: Function prefixes, library-specific patterns, build paths",
            "- WEAK: Generic function names, common terminology",
            "",
            "CONSOLIDATION APPROACH:",
            "- Group ALL evidence by the library project it belongs to",
            "- Combine evidence for the same project into ONE library entry",
            "- Use the main project/repository name as the library name",
            "",
            "QUALITY STANDARDS:",
            "- Only report libraries with credible evidence of source code inclusion",
            "- Be conservative: better to miss a library than report false positives",
            "- Focus on major, independently-developed libraries with clear evidence",
        ]

        if report_custom_components:
            instructions.extend([
                "",
                "CUSTOM/INTERNAL COMPONENT REPORTING:",
                "- Report custom, internal, or proprietary components when identified",
                "- Include analysis of custom tools and internal utilities",
                "- Mark clearly as 'custom/internal' in the library name",
            ])
        else:
            instructions.extend([
                "",
                "CUSTOM/INTERNAL COMPONENT POLICY:",
                "- DO NOT report custom, internal, or proprietary components",
                "- Focus ONLY on well-known open-source third-party libraries",
                "- Exclude analysis of custom tools, internal utilities, or proprietary code",
                "- If the binary appears to be primarily custom/internal code, report an empty library list",
            ])

        if enable_knowledge_base or enable_web_search:
            instructions.append("VERIFICATION RESOURCES:")

        if enable_web_search:
            instructions.append("- Search online to verify library information and resolve ambiguities")

        if enable_knowledge_base:
            instructions.append("- Consult knowledge base for library identification patterns")

        instructions.extend([
            "",
            "RESPONSE FORMAT:",
            "",
            "LIBRARY NAMING PRIORITY (CRITICAL):",
            "1. SOURCE REPOSITORY NAME (highest priority) - Use actual repository/project name",
            "2. COMMON TPL ABBREVIATION - Widely recognized short forms (e.g., 'zlib', 'curl')",
            "3. FULL OFFICIAL NAME - Complete project name if no standard abbreviation",
            "",
            "NAMING RULES:",
            "- Use CURRENT/LATEST project names (not historical names)",
            "- Examples: 'OpenSSL' (not 'openssl'), 'PostgreSQL' (not 'Postgres')",
            "- For renamed projects: use current name, mention old names in description",
            "",
            "FIELD REQUIREMENTS:",
            "- Library name: Follow naming priority above",
            "- Description: Include full name, historical names, and project details",
            "- Evidence type: 'Explicit' (direct mentions), 'Implicit' (patterns), or 'Mixed'",
            "- Evidence list: Specific strings from binary that support this identification",
            "- Reasoning: Clear explanation of why this represents source code inclusion",
            "",
            "Remember: You're identifying source code that was compiled INTO this binary, not libraries it might call or reference."
        ])

        self.agent = Agent(
            model=create_model(),
            tools=tools,
            show_tool_calls=True,
            knowledge=knowledge,
            search_knowledge=enable_knowledge_base,
            instructions=instructions,
            response_model=TPLAnalysisResult,
        )

        # Load knowledge base if exists
        if knowledge is not None:
            self.agent.knowledge.load(recreate=False)

        self.method_name = "Agent Analysis"

    def analyze(self, target_binary: TargetBinary, software_context: SoftwareContext = None) -> (
    List[Library], RunResponse):
        """Analyze binary for library source code inclusion"""



        # Build analysis prompt
        prompt = self._build_analysis_prompt(target_binary, target_binary.classified_strings, software_context)

        # Run agent analysis
        response = self.agent.run(prompt)
        analysis_result = response.content

        # Convert to Library objects
        libraries = []
        for lib_result in analysis_result.libraries:
            library = Library(
                name=lib_result.name,
                description=lib_result.description,
                evidence_type=lib_result.evidence_type,
                evidences=lib_result.evidences,
                reasoning=lib_result.reasoning,
                identify_methods=[self.method_name],
            )
            libraries.append(library)

        return libraries, response

    def _build_analysis_prompt(self, target_binary: TargetBinary, filtered_strings: Dict,
                               software_context: SoftwareContext = None) -> str:
        """Build the analysis prompt for the agent"""

        prompt = f"""BINARY COMPOSITION ANALYSIS - STEP 2: LIBRARY SOURCE CODE IDENTIFICATION

TARGET BINARY:
- Name: {target_binary.binary_name}
- Path: {target_binary.relative_path}  
- Size: {target_binary.file_size_kb} KB
- Type: Binary file for source code composition analysis
"""
        # 添加上下文信息
        if software_context:
            prompt += f"""
SOFTWARE CONTEXT ANALYSIS (confidence: {software_context.confidence_level}):
- Type: {software_context.software_type}
- Purpose: {software_context.primary_purpose}
- Environment: {software_context.deployment_environment}
- Architecture: {software_context.architecture_pattern}
- Build System: {software_context.build_system}
- Technology Stack: {', '.join(software_context.technology_stack)}
- Key Components: {', '.join(software_context.key_components)}

CONTEXT-BASED LIBRARY EXPECTATIONS:
Use this context to prioritize library identification and validate findings against typical patterns for this software type.
        """

        # 修改主要源库信息部分 - 不再强制要求MUST be included
        if target_binary.information and target_binary.information.source_library:
            prompt += f"""
PRELIMINARY IDENTIFICATION (from Step 1 analysis):
- Initial assessment: {target_binary.information.source_library.name}
- Description: {target_binary.information.source_library.description}

NOTE: This is a preliminary identification that should be validated against ALL available evidence.
Your analysis should independently verify whether this identification is accurate based on the symbols, strings, and patterns found.
If evidence contradicts this preliminary assessment, trust the evidence.
"""
        elif target_binary.information:
            prompt += f"""
BINARY IDENTITY (from Step 1 analysis):
- Description: {target_binary.information.description}

TASK: Identify what library projects have source code compiled into this binary.
"""

        # 添加符号分析部分
        if target_binary.exported_symbols:
            symbol_analysis = target_binary.exported_symbol_analysis
            prompt += f"""
EXPORTED SYMBOL EVIDENCE (HIGH PRIORITY):
- Total exported symbols: {symbol_analysis['total_exported']}
- Symbol families by prefix:
"""
            for prefix, info in symbol_analysis['prefix_categories'].items():
                examples_str = ', '.join(info['examples'])
                prompt += f"  • {prefix}_* family: {info['count']} symbols (e.g., {examples_str})\n"

            prompt += """
SYMBOL ANALYSIS GUIDANCE:
- Exported symbols are the most reliable indicator of what this binary actually IS
- Plugin patterns (e.g., 'ao_plugin_*') strongly indicate the source library
- Symbol prefixes reveal the true identity, often more reliable than filename
"""

        if target_binary.imported_symbols:
            import_analysis = target_binary.imported_symbol_analysis
            if import_analysis['significant_prefixes']:
                prompt += f"""
IMPORTED SYMBOL PATTERNS (Dependency Analysis):
- Total imported symbols: {import_analysis['total_imported']}
- Key dependency patterns:
"""
                for prefix, info in import_analysis['significant_prefixes'].items():
                    examples_str = ', '.join(info['examples'])
                    prompt += f"  • {prefix}_* family: {info['count']} symbols (e.g., {examples_str})\n"

        # 动态库排除信息
        if target_binary.dynamic_libraries:
            prompt += f"""
DYNAMIC LIBRARIES (excluded from analysis):
{', '.join(target_binary.dynamic_libraries)}
NOTE: These are runtime dependencies, NOT compiled into the binary. Do not analyze these.
For example: if the binary dynamically links 'libssl.so', and 'libssl.so' is from OpenSSL, 
you should NOT report 'OpenSSL' as a library in this binary, because 'libssl.so' is not 
compiled into this binary - it's just a runtime dependency.
"""

        # 字符串过滤方法说明
        total_filtered = sum(len(v) if isinstance(v, list) else len(v) for v in filtered_strings.values())
        prompt += f"""
STRING ANALYSIS METHODOLOGY:
Our advanced string filtering system extracted {total_filtered} high-value strings from {len(target_binary.strings)} total strings using:

1. LICENSE/COPYRIGHT DETECTION: Broad pattern matching for copyright, license, author information
2. PATH/URL ANALYSIS: Source paths, repository URLs, library file references  
3. FUNCTION PREFIX ANALYSIS: Statistical analysis of function naming patterns
4. LOG MESSAGE EXTRACTION: Error messages, debug info, initialization strings
5. VERSION INFORMATION: Version strings, build info, release identifiers
6. COMPONENT NAME MATCHING: Two-phase matching against about 5,000 known library names:
   - Phase 1: Fast filtering using substring matching
   - Phase 2: Precise word-boundary matching to avoid false positives

COMPONENT MATCHING INTERPRETATION:
The component matches below show potential library references, but require careful analysis:
✓ STRONG INDICATORS: Multiple matches with library-specific patterns, version info, copyright
✓ MEDIUM INDICATORS: Function prefixes, API patterns, but could be external dependencies  
✗ WEAK INDICATORS: Generic terms, single matches, common words that may be coincidental

CRITICAL DISTINCTION:
- Component matches may indicate SOURCE CODE INCLUSION (what we want)
- OR they may indicate EXTERNAL DEPENDENCIES (exclude from results)
- OR they may indicate INTERNAL FUNCTIONALITY (exclude from results)
Your task is to distinguish between these cases using all available evidence.
"""

        # 版权许可证据
        if filtered_strings.get('license_copyright'):
            copyright_items = filtered_strings['license_copyright']
            prompt += f"\nLICENSE/COPYRIGHT EVIDENCE ({len(copyright_items)} items):\n"
            for item in copyright_items[:self.max_display_copyright]:
                prompt += f"• {item}\n"
            if len(copyright_items) > self.max_display_copyright:
                remaining = len(copyright_items) - self.max_display_copyright
                prompt += f"... and {remaining} more copyright/license strings\n"

        # 路径URL证据
        if filtered_strings.get('paths_urls'):
            path_items = filtered_strings['paths_urls']
            prompt += f"\nPATH/URL EVIDENCE ({len(path_items)} items):\n"
            for item in path_items[:self.max_display_paths]:
                prompt += f"• {item}\n"
            if len(path_items) > self.max_display_paths:
                remaining = len(path_items) - self.max_display_paths
                prompt += f"... and {remaining} more path/URL strings\n"

        # 函数前缀模式
        if filtered_strings.get('function_prefixes'):
            prefix_items = filtered_strings['function_prefixes']
            prompt += f"\nFUNCTION PREFIX PATTERNS ({len(prefix_items)} patterns):\n"
            for prefix in prefix_items[:self.max_display_function_prefixes]:
                prompt += f"• {prefix}\n"
            if len(prefix_items) > self.max_display_function_prefixes:
                remaining = len(prefix_items) - self.max_display_function_prefixes
                prompt += f"... and {remaining} more function prefixes\n"

        # 日志错误消息
        if filtered_strings.get('log_messages'):
            log_items = filtered_strings['log_messages']
            prompt += f"\nLOG/ERROR MESSAGES ({len(log_items)} items):\n"
            for msg in log_items[:self.max_display_logs]:
                prompt += f"• {msg}\n"
            if len(log_items) > self.max_display_logs:
                remaining = len(log_items) - self.max_display_logs
                prompt += f"... and {remaining} more log messages\n"

        # 版本信息
        if filtered_strings.get('version_info'):
            version_items = filtered_strings['version_info']
            prompt += f"\nVERSION INFORMATION ({len(version_items)} items):\n"
            for version in version_items[:self.max_display_versions]:
                prompt += f"• {version}\n"
            if len(version_items) > self.max_display_versions:
                remaining = len(version_items) - self.max_display_versions
                prompt += f"... and {remaining} more version strings\n"

        # 组件名匹配结果
        component_matches = filtered_strings.get('component_matches', {})
        if component_matches:
            # 按证据强度排序（匹配数量）
            sorted_components = sorted(component_matches.items(),
                                       key=lambda x: len(x[1]), reverse=True)

            prompt += f"\nCOMPONENT NAME MATCHES ({len(component_matches)} components detected):\n"
            prompt += "Format: [Component] → Evidence strings (showing top matches)\n\n"

            # 显示顶部组件
            for component, matches in sorted_components[:self.max_display_components]:
                match_count = len(matches)
                display_matches = matches[:self.max_matches_per_component]

                prompt += f"[{component}] ({match_count} matches):\n"
                for match in display_matches:
                    prompt += f"  • {match}\n"
                if match_count > self.max_matches_per_component:
                    remaining_matches = match_count - self.max_matches_per_component
                    prompt += f"  ... and {remaining_matches} more matches\n"
                prompt += "\n"

            # 如果还有更多组件未显示
            if len(sorted_components) > self.max_display_components:
                remaining_components = len(sorted_components) - self.max_display_components
                prompt += f"... and {remaining_components} more components with fewer matches\n\n"

            # 组件匹配分析指导
            prompt += "COMPONENT MATCH ANALYSIS GUIDANCE:\n"
            prompt += "• HIGH CONFIDENCE: Components with many matches, specific function patterns, version info\n"
            prompt += "• MEDIUM CONFIDENCE: Components with moderate matches, some specific patterns\n"
            prompt += "• LOW CONFIDENCE: Components with few matches, generic terms, or common words\n"
            prompt += "• FALSE POSITIVES: Generic terms (like 'file', 'server', 'check') that appear in many contexts\n\n"

            # 主导模式分析
            if sorted_components:
                top_component = sorted_components[0]
                prompt += f"DOMINANT PATTERN: '{top_component[0]}' has the most matches ({len(top_component[1])})\n"
                prompt += "Consider whether other matches might be internal modules of this dominant library.\n\n"

        prompt += """
ANALYSIS INSTRUCTIONS:

1. EVIDENCE INTEGRATION WITH SYMBOL PRIORITY:
   - START with exported symbol analysis - this is your most reliable evidence
   - Cross-reference symbol patterns with string evidence and component matches
   - If symbols contradict preliminary identification, trust the symbols
   - Look for CONSISTENT PATTERNS across multiple evidence types

2. SYMBOL-BASED IDENTIFICATION:
   - Exported symbols reveal what this binary actually IS and DOES
   - Plugin patterns (ao_plugin_*, np_*, etc.) strongly indicate source library
   - Function prefixes in symbols are more reliable than string-based prefixes
   - Imported symbols show dependencies, not necessarily source inclusion

3. COMPONENT MATCH INTERPRETATION:
   - COMPILED-IN LIBRARIES: Strong evidence across multiple categories, library-specific patterns
   - EXTERNAL DEPENDENCIES: Component matches but no copyright/path evidence of inclusion
   - INTERNAL MODULES: Component matches that are actually features of a larger library
   - FALSE POSITIVES: Generic terms without supporting technical evidence

4. PRELIMINARY IDENTIFICATION VALIDATION:
   - Validate (don't assume) the preliminary identification from Step 1
   - If symbol evidence contradicts it, explain the discrepancy in your reasoning
   - Trust concrete evidence over naming conventions

5. EVIDENCE STRENGTH HIERARCHY:
   - STRONGEST: Exported symbol patterns + copyright statements + version info
   - STRONG: Symbol patterns + function prefixes + library-specific error messages
   - MEDIUM: Component matches + generic function patterns  
   - WEAK: Component matches alone without supporting evidence

6. QUALITY CONTROL:
   - Be conservative: better to miss a library than report false positives
   - Focus on libraries with multiple types of supporting evidence
   - Exclude generic matches without technical substance
   - Consider the binary's primary purpose when evaluating matches

TASK: Identify all library projects whose source code is compiled into this binary.
Prioritize exported symbol evidence, then validate with comprehensive evidence analysis.
Focus on independent libraries with strong, consistent evidence across multiple categories.
"""

        return prompt