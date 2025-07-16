from typing import List, Dict

from agno.run.response import RunResponse
from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

from app.config import settings
from app.interface import TargetBinary, Library
from app.tpl_detection.agent_analysis.response_models import TPLAnalysisResult
from app.tpl_detection.agent_analysis.model_factory import create_model
from agno.tools.duckduckgo import DuckDuckGoTools

from app.tpl_detection.agent_analysis.string_filter import StringFilter


class TPLAnalyzer:
    def __init__(self,
                 knowledge_json_path: str = None,
                 enable_web_search: bool = True,
                 enable_knowledge_base: bool = True,
                 report_custom_components: bool = False,
                 max_paths: int = 20,
                 max_functions: int = 20,
                 max_logs: int = 15,
                 max_string_length: int = 200):

        self.string_filter = StringFilter(max_paths, max_functions, max_logs, max_string_length)

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

        # 核心指令系统 - 完全重写
        instructions = [
            "You are an expert binary composition analyst specializing in library source code identification.",
            "",
            "WORKFLOW CONTEXT:",
            "This is STEP 2 of a 3-step binary composition analysis workflow:",
            "• STEP 1 (completed): Binary identity analysis identified the primary source",
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
            "PRIORITY SYSTEM:",
            "1. PRIMARY SOURCE LIBRARY: If step 1 identified a source library, it MUST be included",
            "2. DIRECT DEPENDENCIES: Libraries this project directly incorporates",
            "3. TRANSITIVE DEPENDENCIES: Libraries included by the dependencies",
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
            "✅ CORRECT: Custom app with OpenSSL copyright → Report 'OpenSSL'",
            "❌ WRONG: Report both 'OpenSSL' and 'BoringSSL' (competing implementations)",
            "❌ WRONG: Report 'libcrypto' separately from 'OpenSSL' (same project)",
            "",
            "EVIDENCE ANALYSIS:",
            "- STRONG: Copyright/license statements, version strings, project URLs",
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

    def analyze(self, target_binary: TargetBinary) -> (List[Library], RunResponse):
        """Analyze binary for library source code inclusion"""

        # Filter and categorize strings
        filtered_strings = self.string_filter.filter_strings(target_binary.strings)

        # Build analysis prompt
        prompt = self._build_analysis_prompt(target_binary, filtered_strings)

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

    def _build_analysis_prompt(self, target_binary: TargetBinary, filtered_strings: Dict) -> str:
        """Build the analysis prompt for the agent"""

        prompt = f"""BINARY COMPOSITION ANALYSIS - STEP 2: LIBRARY SOURCE CODE IDENTIFICATION

    TARGET BINARY:
    - Name: {target_binary.binary_name}
    - Path: {target_binary.relative_path}  
    - Size: {target_binary.file_size_kb} KB
    - Type: Binary file for source code composition analysis
    """

        # 添加主要源库信息（最重要的上下文）
        if target_binary.information and target_binary.information.source_library:
            prompt += f"""
    PRIMARY SOURCE LIBRARY (from Step 1 analysis):
    - Library: {target_binary.information.source_library.name}
    - Description: {target_binary.information.source_library.description}

    CRITICAL: This primary source library represents the main codebase and MUST be included in your analysis.
    All evidence related to this library should be consolidated under this primary library entry.
    """
        elif target_binary.information:
            prompt += f"""
    BINARY IDENTITY (from Step 1 analysis):
    - Description: {target_binary.information.description}

    TASK: Identify what library projects have source code compiled into this binary.
    """

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

        # STRING FILTERING METHODOLOGY
        prompt += f"""
    STRING ANALYSIS METHODOLOGY:
    Our advanced string filtering system extracted {sum(len(v) if isinstance(v, list) else len(v) for v in filtered_strings.values())} high-value strings from {len(target_binary.strings)} total strings using:

    1. LICENSE/COPYRIGHT DETECTION: Broad pattern matching for copyright, license, author information
    2. PATH/URL ANALYSIS: Source paths, repository URLs, library file references  
    3. FUNCTION PREFIX ANALYSIS: Statistical analysis of function naming patterns
    4. LOG MESSAGE EXTRACTION: Error messages, debug info, initialization strings
    5. VERSION INFORMATION: Version strings, build info, release identifiers
    6. COMPONENT NAME MATCHING: Two-phase matching against {len(self.string_filter.known_component_names)} known library names:
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

        # 字符串证据分析
        if filtered_strings.get('license_copyright'):
            prompt += f"\nLICENSE/COPYRIGHT EVIDENCE ({len(filtered_strings['license_copyright'])} items):\n"
            for item in filtered_strings['license_copyright'][:10]:  # 限制显示数量
                prompt += f"• {item}\n"
            if len(filtered_strings['license_copyright']) > 10:
                prompt += f"... and {len(filtered_strings['license_copyright']) - 10} more copyright/license strings\n"

        if filtered_strings.get('paths_urls'):
            prompt += f"\nPATH/URL EVIDENCE ({len(filtered_strings['paths_urls'])} items):\n"
            for item in filtered_strings['paths_urls'][:8]:
                prompt += f"• {item}\n"
            if len(filtered_strings['paths_urls']) > 8:
                prompt += f"... and {len(filtered_strings['paths_urls']) - 8} more path/URL strings\n"

        if filtered_strings.get('function_prefixes'):
            prompt += f"\nFUNCTION PREFIX PATTERNS ({len(filtered_strings['function_prefixes'])} patterns):\n"
            for prefix in filtered_strings['function_prefixes'][:10]:
                prompt += f"• {prefix}\n"
            if len(filtered_strings['function_prefixes']) > 10:
                prompt += f"... and {len(filtered_strings['function_prefixes']) - 10} more function prefixes\n"

        if filtered_strings.get('log_messages'):
            prompt += f"\nLOG/ERROR MESSAGES ({len(filtered_strings['log_messages'])} items):\n"
            for msg in filtered_strings['log_messages'][:8]:
                prompt += f"• {msg}\n"
            if len(filtered_strings['log_messages']) > 8:
                prompt += f"... and {len(filtered_strings['log_messages']) - 8} more log messages\n"

        if filtered_strings.get('version_info'):
            prompt += f"\nVERSION INFORMATION ({len(filtered_strings['version_info'])} items):\n"
            for version in filtered_strings['version_info'][:5]:
                prompt += f"• {version}\n"
            if len(filtered_strings['version_info']) > 5:
                prompt += f"... and {len(filtered_strings['version_info']) - 5} more version strings\n"

        # COMPONENT MATCHING RESULTS
        component_matches = filtered_strings.get('component_matches', {})
        if component_matches:
            # Sort components by evidence strength (number of matches)
            sorted_components = sorted(component_matches.items(),
                                       key=lambda x: len(x[1]), reverse=True)

            prompt += f"\nCOMPONENT NAME MATCHES ({len(component_matches)} components detected):\n"
            prompt += "Format: [Component] → Evidence strings (showing top matches)\n\n"

            for component, matches in sorted_components[:15]:  # Show top 15 components
                match_count = len(matches)
                display_matches = matches[:3]  # Show top 3 matches per component

                prompt += f"[{component}] ({match_count} matches):\n"
                for match in display_matches:
                    prompt += f"  • {match}\n"
                if match_count > 3:
                    prompt += f"  ... and {match_count - 3} more matches\n"
                prompt += "\n"

            if len(sorted_components) > 15:
                remaining = len(sorted_components) - 15
                prompt += f"... and {remaining} more components with fewer matches\n\n"

            # Analysis guidance for component matches
            prompt += "COMPONENT MATCH ANALYSIS GUIDANCE:\n"
            prompt += "• HIGH CONFIDENCE: Components with many matches, specific function patterns, version info\n"
            prompt += "• MEDIUM CONFIDENCE: Components with moderate matches, some specific patterns\n"
            prompt += "• LOW CONFIDENCE: Components with few matches, generic terms, or common words\n"
            prompt += "• FALSE POSITIVES: Generic terms (like 'file', 'server', 'check') that appear in many contexts\n\n"

            # Suggest dominant library analysis
            if sorted_components:
                top_component = sorted_components[0]
                prompt += f"DOMINANT PATTERN: '{top_component[0]}' has the most matches ({len(top_component[1])})\n"
                prompt += "Consider whether other matches might be internal modules of this dominant library.\n\n"

        prompt += f"""
    ANALYSIS INSTRUCTIONS:

    1. EVIDENCE INTEGRATION:
       - Synthesize ALL evidence types: copyright, paths, functions, logs, versions, component matches
       - Component matches are HINTS, not definitive proof - validate with other evidence
       - Look for CONSISTENT PATTERNS across multiple evidence types

    2. COMPONENT MATCH INTERPRETATION:
       - COMPILED-IN LIBRARIES: Strong evidence across multiple categories, library-specific patterns
       - EXTERNAL DEPENDENCIES: Component matches but no copyright/path evidence of inclusion
       - INTERNAL MODULES: Component matches that are actually features of a larger library
       - FALSE POSITIVES: Generic terms without supporting technical evidence

    3. CONSOLIDATION PRIORITY:
       - Start with the primary source library (if identified in Step 1)
       - Group related component matches under their parent library project
       - Example: If binary is 'openssl', then 'base64', 'ed25519' matches are likely OpenSSL features
       - Do NOT create separate entries for sub-components of the same library

    4. EVIDENCE STRENGTH HIERARCHY:
       - STRONGEST: Copyright statements + source paths + version info + component matches
       - STRONG: Function prefixes + library-specific error messages + component matches  
       - MEDIUM: Component matches + generic function patterns
       - WEAK: Component matches alone without supporting evidence

    5. QUALITY CONTROL:
       - Be conservative: better to miss a library than report false positives
       - Focus on libraries with multiple types of supporting evidence
       - Exclude generic matches without technical substance
       - Consider the binary's primary purpose when evaluating matches

    TASK: Identify all library projects whose source code is compiled into this binary.
    Use component matches as starting points, but validate with comprehensive evidence analysis.
    Focus on independent libraries with strong, consistent evidence across multiple categories.
    """

        return prompt