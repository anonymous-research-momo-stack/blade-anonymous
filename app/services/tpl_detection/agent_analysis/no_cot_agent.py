from typing import List, Dict

from agno.run.response import RunResponse
from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

from ....config import settings
from ....interface import TargetBinary, Library
from .response_models import TPLAnalysisResult, SoftwareContext
from .model_factory import create_model
from agno.tools.duckduckgo import DuckDuckGoTools


class NoCOTTPLAnalyzer:
    def __init__(self,

                 # Prompt display limits
                 max_display_copyright: int = 10,  # Number of copyright/license strings to show in the prompt
                 max_display_paths: int = 8,  # Number of path/URL strings to show in the prompt
                 max_display_function_prefixes: int = 10,  # Number of function prefixes to show in the prompt
                 max_display_logs: int = 8,  # Number of log messages to show in the prompt
                 max_display_versions: int = 5,  # Number of version strings to show in the prompt
                 max_display_components: int = 5,  # Number of components to display in the prompt
                 max_matches_per_component: int = 3,  # Number of match examples per component to display
                 ):

        # Prompt display parameter configuration
        self.max_display_copyright = max_display_copyright  # Upper limit for copyright/license display
        self.max_display_paths = max_display_paths  # Upper limit for path/URL display
        self.max_display_function_prefixes = max_display_function_prefixes  # Upper limit for function prefixes display
        self.max_display_logs = max_display_logs  # Upper limit for log messages display
        self.max_display_versions = max_display_versions  # Upper limit for version info display
        self.max_display_components = max_display_components  # Upper limit for component matches display
        self.max_matches_per_component = max_matches_per_component  # Number of examples per component


        self.agent = Agent(
            model=create_model(),
            show_tool_calls=True,
            response_model=TPLAnalysisResult,
        )

        self.method_name = "Agent Analysis"

    def analyze(self, target_binary: TargetBinary,
                candidate_libraries_from_feature_matching: List[Library] = None) -> (List[Library], RunResponse):
        """Analyze binary for library source code inclusion"""



        # Build analysis prompt
        prompt = self._build_analysis_prompt(target_binary,
                                             target_binary.classified_strings,
                                             candidate_libraries_from_feature_matching)

        # Run agent analysis
        response = self.agent.run(prompt)
        analysis_result = response.content

        # Convert to Library objects
        libraries = []
        # print(analysis_result.analysis_summary)
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
                               candidate_libraries_from_feature_matching: List[Library] = None) -> str:
        """Build the analysis prompt for the agent"""

        prompt = f"""
Analyze the reused third-party in this binary file.

TARGET BINARY:
- Name: {target_binary.binary_name}
- Path: {target_binary.relative_path}  
- Size: {target_binary.file_size_kb} KB
- Type: Binary file for source code composition analysis

"""

        # Add symbol analysis section
        if target_binary.exported_symbols:
            symbol_analysis = target_binary.exported_symbol_analysis
            prompt += f"""
- exported symbols: {symbol_analysis['total_exported']}
"""


        if target_binary.imported_symbols:
            import_analysis = target_binary.imported_symbol_analysis
            if import_analysis['significant_prefixes']:
                prompt += f"""
imported symbols: {import_analysis['total_imported']}
"""

        # Dynamic library exclusion info
        if target_binary.dynamic_libraries:
            prompt += f"""
DYNAMIC Dependencies:
{', '.join(target_binary.dynamic_libraries)}
"""

        # License/Copyright evidence
        if filtered_strings.get('license_copyright'):
            copyright_items = filtered_strings['license_copyright']
            prompt += f"\nLICENSE/COPYRIGHT EVIDENCE ({len(copyright_items)} items):\n"
            for item in copyright_items[:self.max_display_copyright]:
                prompt += f"• {item}\n"
            if len(copyright_items) > self.max_display_copyright:
                remaining = len(copyright_items) - self.max_display_copyright
                prompt += f"... and {remaining} more copyright/license strings\n"

        # Path/URL evidence
        if filtered_strings.get('paths_urls'):
            path_items = filtered_strings['paths_urls']
            prompt += f"\nPATH/URL EVIDENCE ({len(path_items)} items):\n"
            for item in path_items[:self.max_display_paths]:
                prompt += f"• {item}\n"
            if len(path_items) > self.max_display_paths:
                remaining = len(path_items) - self.max_display_paths
                prompt += f"... and {remaining} more path/URL strings\n"

        # Function prefix patterns
        if filtered_strings.get('function_prefixes'):
            prefix_items = filtered_strings['function_prefixes']
            prompt += f"\nFUNCTION PREFIX PATTERNS ({len(prefix_items)} patterns):\n"
            for prefix in prefix_items[:self.max_display_function_prefixes]:
                prompt += f"• {prefix}\n"
            if len(prefix_items) > self.max_display_function_prefixes:
                remaining = len(prefix_items) - self.max_display_function_prefixes
                prompt += f"... and {remaining} more function prefixes\n"

        # Log/error messages
        if filtered_strings.get('log_messages'):
            log_items = filtered_strings['log_messages']
            prompt += f"\nLOG/ERROR MESSAGES ({len(log_items)} items):\n"
            for msg in log_items[:self.max_display_logs]:
                prompt += f"• {msg}\n"
            if len(log_items) > self.max_display_logs:
                remaining = len(log_items) - self.max_display_logs
                prompt += f"... and {remaining} more log messages\n"

        # Version information
        if filtered_strings.get('version_info'):
            version_items = filtered_strings['version_info']
            prompt += f"\nVERSION INFORMATION ({len(version_items)} items):\n"
            for version in version_items[:self.max_display_versions]:
                prompt += f"• {version}\n"
            if len(version_items) > self.max_display_versions:
                remaining = len(version_items) - self.max_display_versions
                prompt += f"... and {remaining} more version strings\n"

        for i, lib in enumerate(candidate_libraries_from_feature_matching, 1):
            prompt += f"\n{i}. LIBRARY: {lib.name}"
            if lib.description:
                prompt += f"\n   Description: {lib.description[:150]}..."

            prompt += f"\n   Detection Methods: {', '.join(lib.identify_methods)}"

            if lib.matched_strings:
                match_count = len(lib.matched_strings)
                if match_count <= 2:
                    examples = ", ".join(lib.matched_strings)
                else:
                    examples = ", ".join(lib.matched_strings[:2]) + f"... (+{match_count - 2} more)"
                prompt += f"\n   Evidence ({match_count} features): {examples}"

            prompt += "\n"

        return prompt