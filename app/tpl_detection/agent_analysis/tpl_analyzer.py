from typing import List, Dict

from agno.run.response import RunResponse
from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

from app.config import settings
from app.interface import TargetBinary, Library
from app.tpl_detection.agent_analysis.response_models import TPLAnalysisResult
from app.tpl_detection.agent_analysis.string_filter import StringFilter
from app.tpl_detection.agent_analysis.model_factory import create_model
from agno.tools.duckduckgo import DuckDuckGoTools


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

        # Build instructions
        instructions = [
            "You are an expert in binary composition analysis. Your task is to identify DISTINCT LIBRARIES whose code is included in this binary file.",

            "CRITICAL DEFINITION: A 'library' means code from a SEPARATE, INDEPENDENTLY DEVELOPED project or repository.",
            "- Each library should represent ONE source code repository or project",
            "- Do NOT separate a library into its sub-components or modules",
            "- Do NOT report protocol implementations or feature modules as separate libraries",

            "EXAMPLES OF CORRECT vs INCORRECT identification:",
            "✅ CORRECT: 'OpenSSL' (the entire cryptographic library)",
            "❌ INCORRECT: 'libcrypto', 'libssl', 'CMS', 'TS' (these are OpenSSL components, not separate libraries)",
            "✅ CORRECT: 'zlib' (independent compression library)",
            "❌ INCORRECT: 'inflate', 'deflate' (these are zlib functions, not separate libraries)",
            "✅ CORRECT: 'SQLite' (independent database library)",
            "❌ INCORRECT: 'sqlite3_exec', 'sqlite3_open' (these are SQLite functions, not separate libraries)",

            "ANALYSIS APPROACH:",
            "1. ALWAYS include the main source library identified in previous analysis",
            "2. Look for evidence of OTHER independent libraries that were statically linked",
            "3. Group all evidence by the library/project it belongs to",
            "4. Report each independent library/project only ONCE",

            "WHAT TO IDENTIFY (independent libraries only):",
            "- OpenSSL (entire cryptographic library and toolkit)",
            "- zlib (compression library)",
            "- SQLite (database library)",
            "- libcurl (HTTP client library)",
            "- libxml2 (XML parsing library)",
            "- Other independently developed and maintained libraries",

            "WHAT NOT TO IDENTIFY:",
            "- Sub-components of libraries (libcrypto, libssl are parts of OpenSSL)",
            "- Protocol implementations (CMS, TS are OpenSSL features)",
            "- Function modules or feature sets within a library",
            "- System libraries that are dynamically linked",
            "- Internal functionality or built-in features",

            "EVIDENCE CONSOLIDATION:",
            "- If you see OpenSSL copyright + SSL_ functions + crypto_ functions → Report as 'OpenSSL'",
            "- If you see zlib copyright + inflate/deflate functions → Report as 'zlib'",
            "- If you see multiple pieces of evidence for the same library → Combine into ONE library entry",

            "OUTPUT FORMAT:",
            "- Library name: Use the main project/repository name",
            "- Description: Describe the entire library, not just one component",
            "- Evidence type: 'Explicit' (copyright/license), 'Implicit' (function patterns), or 'Mixed'",
            "- Combine ALL evidence for the same library into one entry",
            "- Reasoning: Explain why this represents an independent library project",

            "Be conservative - only report libraries with strong evidence of being SEPARATE, INDEPENDENT projects."
        ]

        if enable_knowledge_base or enable_web_search:
            instructions.append("If you need more information about potential libraries:")

        if enable_web_search:
            instructions.append("- Search the web for library information and confirmation")

        if enable_knowledge_base:
            instructions.append("- Consult the knowledge base for library patterns and signatures")

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
        """Analyze binary for third-party library usage"""

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

        prompt = f"""Analyze this binary for library composition - identify ALL libraries whose code is present in this binary:

Binary Information:
- Name: {target_binary.binary_name}
- Path: {target_binary.relative_path}
- Size: {target_binary.file_size_kb} KB
"""

        # Add dynamic libraries info
        if target_binary.dynamic_libraries:
            prompt += f"""
Dynamic Libraries (loaded at runtime, NOT compiled in):
{', '.join(target_binary.dynamic_libraries)}

IMPORTANT: These dynamic libraries are loaded at runtime and their code is NOT compiled into this binary.
Do NOT identify these as embedded libraries. Focus only on code that is statically compiled in.
"""

        # Add previous analysis info if available
        if target_binary.information and target_binary.information.source_library:
            prompt += f"""
Previous Analysis Results:
- Source Library: {target_binary.information.source_library.name}
- Description: {target_binary.information.source_library.description}

NOTE: This source library should be included in your analysis as it represents the main library code in this binary.
"""

        # Add filtered strings
        if filtered_strings['license_copyright']:
            prompt += f"\nLicense/Copyright Strings ({len(filtered_strings['license_copyright'])}):\n"
            for item in filtered_strings['license_copyright']:
                prompt += f"- {item}\n"

        if filtered_strings['paths_urls']:
            prompt += f"\nFile Paths/URLs ({len(filtered_strings['paths_urls'])}):\n"
            for item in filtered_strings['paths_urls']:
                prompt += f"- {item}\n"

        functions = filtered_strings['functions']
        if functions['function_prefixes']:
            prompt += f"\nFunction Prefixes (top {len(functions['function_prefixes'])}):\n"
            for prefix in functions['function_prefixes']:
                prompt += f"- {prefix}\n"

        if functions['demangled_functions']:
            prompt += f"\nDemangled Functions ({len(functions['demangled_functions'])}):\n"
            for func in functions['demangled_functions']:
                prompt += f"- {func}\n"

        if filtered_strings['log_messages']:
            prompt += f"\nLog Messages ({len(filtered_strings['log_messages'])}):\n"
            for msg in filtered_strings['log_messages']:
                prompt += f"- {msg}\n"

        prompt += """
Analyze these artifacts to identify DISTINCT, INDEPENDENT libraries whose code is compiled into this binary.

CRITICAL RULES:
1. Report each independent library/project only ONCE
2. Do NOT separate libraries into sub-components (e.g., don't report both 'OpenSSL' and 'libcrypto')
3. Do NOT report protocol implementations or feature modules as separate libraries
4. Group ALL evidence for the same library into ONE entry

CONSOLIDATION EXAMPLES:
- If you find OpenSSL copyright + SSL_ functions + BN_ functions + EVP_ functions → Report as ONE entry: 'OpenSSL'
- If you find zlib evidence + inflate/deflate functions → Report as ONE entry: 'zlib'
- Do NOT report 'libcrypto' and 'libssl' separately from 'OpenSSL'
- Do NOT report 'CMS' or 'TS' as separate libraries (they are OpenSSL features)

Focus on identifying code from DIFFERENT source repositories or independent projects.
Each library should represent a separately developed and maintained codebase."""

        return prompt