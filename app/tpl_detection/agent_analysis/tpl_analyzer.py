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

        if enable_knowledge_base or enable_web_search:
            instructions.append("VERIFICATION RESOURCES:")

        if enable_web_search:
            instructions.append("- Search online to verify library information and resolve ambiguities")

        if enable_knowledge_base:
            instructions.append("- Consult knowledge base for library identification patterns")

        instructions.extend([
            "",
            "RESPONSE FORMAT:",
            "- Library name: Use main project/repository name (e.g., 'OpenSSL', not 'libssl')",
            "- Description: Brief but complete description of the entire library project",
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
For example: if the binary dynamic linked the 'libssl.so', and we know 'libssl.so' is from OpenSSL, you should not report 'OpenSSL' as a library in this binary. Because the 'libssl.so' is not compiled into this binary, it is just a runtime dependency.
"""

        # 字符串证据分析
        if filtered_strings['license_copyright']:
            prompt += f"\nLICENSE/COPYRIGHT EVIDENCE ({len(filtered_strings['license_copyright'])} items):\n"
            for item in filtered_strings['license_copyright'][:10]:  # 限制显示数量
                prompt += f"• {item}\n"
            if len(filtered_strings['license_copyright']) > 10:
                prompt += f"... and {len(filtered_strings['license_copyright']) - 10} more copyright/license strings\n"

        if filtered_strings['paths_urls']:
            prompt += f"\nPATH/URL EVIDENCE ({len(filtered_strings['paths_urls'])} items):\n"
            for item in filtered_strings['paths_urls'][:8]:
                prompt += f"• {item}\n"
            if len(filtered_strings['paths_urls']) > 8:
                prompt += f"... and {len(filtered_strings['paths_urls']) - 8} more path/URL strings\n"

        functions = filtered_strings['functions']
        if functions['function_prefixes']:
            prompt += f"\nFUNCTION PREFIX PATTERNS ({len(functions['function_prefixes'])} patterns):\n"
            for prefix in functions['function_prefixes'][:10]:
                prompt += f"• {prefix}\n"
            if len(functions['function_prefixes']) > 10:
                prompt += f"... and {len(functions['function_prefixes']) - 10} more function prefixes\n"

        if functions['demangled_functions']:
            prompt += f"\nDEMANGLED FUNCTION SIGNATURES ({len(functions['demangled_functions'])} functions):\n"
            for func in functions['demangled_functions'][:8]:
                prompt += f"• {func}\n"
            if len(functions['demangled_functions']) > 8:
                prompt += f"... and {len(functions['demangled_functions']) - 8} more function signatures\n"

        if filtered_strings['library_signatures']:
            prompt += f"\nLIBRARY SIGNATURE PATTERNS ({len(filtered_strings['library_signatures'])} patterns):\n"
            for sig in filtered_strings['library_signatures'][:10]:
                prompt += f"• {sig}\n"
            if len(filtered_strings['library_signatures']) > 10:
                prompt += f"... and {len(filtered_strings['library_signatures']) - 10} more signature patterns\n"

        if filtered_strings['version_info']:
            prompt += f"\nVERSION INFORMATION ({len(filtered_strings['version_info'])} items):\n"
            for version in filtered_strings['version_info'][:5]:
                prompt += f"• {version}\n"

        prompt += f"""

ANALYSIS INSTRUCTIONS:

1. CONSOLIDATION PRIORITY:
   - Start with the primary source library (if identified in Step 1)
   - Group all related evidence under the correct library project
   - Do NOT create separate entries for sub-components of the same library

2. EVIDENCE EVALUATION:
   - Copyright/license statements = STRONG evidence of source code inclusion
   - Function prefixes + library signatures = MEDIUM evidence
   - Generic patterns without specific attribution = WEAK evidence  

3. LIBRARY IDENTIFICATION STANDARDS:
   - Use main project names (e.g., "OpenSSL" not "libssl" or "libcrypto")
   - Each library should represent ONE independent source code repository
   - Only report libraries with credible evidence of code compilation

4. CONSOLIDATION EXAMPLES:
   - OpenSSL copyright + SSL_* functions + BN_* functions → ONE entry: "OpenSSL"
   - zlib copyright + inflate/deflate functions → ONE entry: "zlib"  
   - Multiple XML-related patterns → Determine if from one library (libxml2) or multiple

TASK: Identify all library projects whose source code is compiled into this binary.
Focus on independent libraries with clear evidence. Consolidate all evidence by source project.
"""

        return prompt