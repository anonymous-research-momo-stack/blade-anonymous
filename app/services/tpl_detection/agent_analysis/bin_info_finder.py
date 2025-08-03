from typing import Optional
from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

from ...config import settings
from ...interface import TargetBinary
from .response_models import BinaryInformation, SoftwareContext
from .model_factory import create_model
from agno.tools.duckduckgo import DuckDuckGoTools


class BinaryInformationFinder:
    def __init__(self,
                 knowledge_json_path: str = None,
                 enable_web_search: bool = True,
                 enable_knowledge_base: bool = True):

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
                    table_name="json_documents",
                    db_url=settings.KNOWLEDGE_DATABASE_URL,
                    search_type=SearchType.hybrid
                ),
            )

        # Enhanced instructions with symbol analysis emphasis
        instructions = [
            "You are a binary analysis specialist focused on identifying binary files through external intelligence and pattern recognition.",
            "",
            "CORE MISSION: Quickly identify what this binary IS using file-level information and external knowledge sources.",
            "This provides foundational context for subsequent detailed internal analysis.",
            "",
            "ANALYSIS STRATEGY:",
            "- PRIORITIZE exported symbol analysis - symbols reveal the true identity",
            "- Leverage file naming patterns and conventions (but symbols override names)",
            "- Use software context when available to improve accuracy",
            "- Consult external knowledge sources for verification",
            "- Focus on establishing binary identity rather than detailed composition",
            "",
            "CRITICAL EVIDENCE HIERARCHY:",
            "1. EXPORTED SYMBOLS (Highest Priority) - The most reliable indicator of what this binary actually IS",
            "2. Function prefix patterns reveal the library's true identity (e.g., 'ao_plugin_*' indicates libao plugin)",
            "3. File names can be misleading, but exported symbols don't lie",
            "4. Context and external knowledge sources provide validation",
            "",
            "SYMBOL-BASED IDENTIFICATION PRINCIPLES:",
            "- If symbols show clear patterns (e.g., 'ssl_*', 'crypto_*'), prioritize over filename",
            "- Plugin patterns (e.g., 'ao_plugin_*', 'np_*') indicate wrapper/plugin architecture",
            "- Consider that filename might reflect the plugin's target, not its source",
            "- Multiple prefixes may indicate which library is the primary source vs. which is being used",
            "",
            "KEY IDENTIFICATION TASKS:",
            "1. BINARY IDENTITY: What type of binary file is this?",
            "2. PRIMARY FUNCTION: What is its main purpose and functionality?",
            "3. SOURCE LIBRARY: Does this binary come from a specific library/project?",
            "",
            "SOURCE LIBRARY IDENTIFICATION PRINCIPLES:",
            "- Strong symbol-based evidence takes priority over name-based evidence",
            "- Plugin architectures: 'ao_plugin_*' symbols → libao plugin, regardless of filename",
            "- Library file conventions (e.g., 'libssl.a' → OpenSSL project)",
            "- Known project patterns and naming conventions",
            "- Only identify when confident about the relationship",
            "",
            "PLUGIN ARCHITECTURE RECOGNITION:",
            "- Plugins often have misleading filenames (e.g., libpulse.so that's actually a libao plugin)",
            "- Symbol patterns are the key: 'ao_plugin_*' = libao plugin, 'pa_*' = PulseAudio client",
            "- Distinguish between what the plugin IS vs. what it interfaces with",
            "",
            "HANDLING UNCERTAIN CASES:",
            "- Custom/demo binaries (e.g., 'demo', 'test', 'myapp'): Usually no identifiable source library",
            "- Generic names (e.g., 'app', 'tool', 'main'): Unlikely to have known source library",
            "- Unknown binaries: Acknowledge when search yields no results",
            "- Be honest about limitations - 'not found' is a valid result",
            "",
            "SEARCH RESULT HANDLING:",
            "- If web search finds no relevant information → state this clearly",
            "- If knowledge base has no matches → acknowledge the limitation",
            "- Don't guess or invent source libraries based on weak evidence",
            "- Custom applications typically don't have identifiable source libraries",
            "",
            "CONTEXT-AWARE ANALYSIS:",
            "- When software context is available, use it to validate findings",
            "- Consider deployment environment for binary role assessment",
            "- Leverage technology stack information for better identification",
            "",
            "CRITICAL EXAMPLES:",
            "✅ Binary 'openssl' → Source Library: OpenSSL (binary IS the OpenSSL toolkit)",
            "✅ Binary 'libssl.a' → Source Library: OpenSSL (libssl is part of OpenSSL project)",
            "✅ Binary 'libpulse.so' with 'ao_plugin_*' symbols → Source Library: libao (plugin architecture)",
            "✅ Binary 'nginx' → Source Library: Nginx (binary IS the nginx web server)",
            "✅ Binary 'sqlite3' → Source Library: SQLite (binary IS the SQLite tool)",
            "❌ Binary 'demo' → Source Library: None (custom/demo applications have no identifiable source)",
            "❌ Binary 'myapp' → Source Library: None (unless clear evidence of specific project origin)",
            "❌ Binary 'test123' → Source Library: None (arbitrary names indicate custom development)",
            "",
            "EFFICIENCY FOCUS:",
            "- This is a rapid identification phase",
            "- Detailed composition analysis happens in subsequent steps",
            "- Focus on establishing clear binary identity and primary source",
            "- Be conservative with source library identification, but trust symbol evidence",
        ]

        # Add resource-specific instructions
        if enable_knowledge_base or enable_web_search:
            instructions.append("VERIFICATION RESOURCES:")

        if enable_web_search:
            instructions.append("- Search online to verify binary identity and source project relationships")

        if enable_knowledge_base:
            instructions.append("- Consult knowledge base for known binary-to-library mappings")

        instructions.extend([
            "",
            "RESPONSE REQUIREMENTS:",
            "- Binary name: Normalized name of the binary",
            "- Description: Comprehensive description covering identity, purpose, and context",
            "- Source library: Based primarily on symbol analysis, secondarily on naming patterns",
            "",
            "Remember: Exported symbols are the most reliable indicator of a binary's true identity.",
            "This analysis establishes the foundation for subsequent detailed library composition analysis."
        ])

        self.agent = Agent(
            model=create_model(),
            tools=tools,
            show_tool_calls=True,
            knowledge=knowledge,
            search_knowledge=enable_knowledge_base,
            instructions=instructions,
            response_model=BinaryInformation,
        )

        # Load knowledge base if exists
        if knowledge is not None:
            self.agent.knowledge.load(recreate=False)


    def find_for(self, target_binary: TargetBinary, software_context: Optional[SoftwareContext] = None):
        """
        Analyze binary file to identify its primary source and composition context

        :param target_binary: Target binary to analyze
        :param software_context: Optional software context for enhanced analysis
        :return: response containing binary information
        """

        # Build context-aware prompt
        task_prompt = self._build_context_aware_prompt(target_binary, software_context)

        response = self.agent.run(task_prompt)
        binary_info = response.content
        target_binary.information = binary_info

        return response

    def _build_context_aware_prompt(self, target_binary: TargetBinary,
                                    software_context: Optional[SoftwareContext]) -> str:
        """Build context-aware analysis prompt with symbol analysis"""

        prompt = f"""BINARY IDENTIFICATION ANALYSIS

BINARY DETAILS:
- Name: {target_binary.binary_name}
- Size: {target_binary.file_size_kb} KB
- Path: {target_binary.relative_path}
"""

        # Add exported symbol analysis
        if target_binary.exported_symbols:
            symbol_analysis = target_binary.exported_symbol_analysis
            prompt += f"""
EXPORTED SYMBOL ANALYSIS (CRITICAL EVIDENCE):
- Total exported symbols: {symbol_analysis['total_exported']}
- Symbol categories by prefix:
"""
            for prefix, info in symbol_analysis['prefix_categories'].items():
                examples_str = ', '.join(info['examples'])
                prompt += f"  • {prefix}_* family: {info['count']} symbols (e.g., {examples_str})\n"
        else:
            prompt += "\nEXPORTED SYMBOL ANALYSIS: No exported symbols available\n"

        # Add imported symbol analysis
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

        # Add dynamic libraries info
        if target_binary.dynamic_libraries:
            prompt += f"""
DYNAMIC LIBRARY DEPENDENCIES:
- Libraries: {', '.join(target_binary.dynamic_libraries)}
- Note: These are runtime dependencies, not the binary's source identity
"""

        # Add software context if available
        if software_context and software_context.confidence_level in ["HIGH", "MEDIUM"]:
            prompt += f"""
SOFTWARE CONTEXT:
- Software Type: {software_context.software_type}
- Primary Purpose: {software_context.primary_purpose}
- Deployment Environment: {software_context.deployment_environment}
- Technology Stack: {', '.join(software_context.technology_stack)}
- Architecture Pattern: {software_context.architecture_pattern}
- Confidence: {software_context.confidence_level}

CONTEXT GUIDANCE:
Use this software context to:
1. Validate binary identification against expected software type
2. Consider deployment environment when assessing binary role
3. Leverage technology stack information for better source identification
4. Apply context-specific validation of findings

Context Analysis Summary: {software_context.directory_analysis}
"""
        else:
            prompt += """
SOFTWARE CONTEXT: No reliable software context available.
Proceed with standalone binary identification based on file-level information.
"""

        prompt += f"""
ANALYSIS REQUIREMENTS:

1. SYMBOL-FIRST BINARY IDENTITY ANALYSIS:
   - PRIORITIZE exported symbol patterns over filename
   - What do the symbol prefixes reveal about this binary's true identity?
   - Plugin patterns (ao_plugin_*, np_*, etc.) indicate wrapper/plugin architecture
   - What type of binary is this? (executable, static library, shared library, plugin, etc.)
   - What is its primary function and purpose based on symbols?

2. SOURCE LIBRARY IDENTIFICATION:
   - Which library project do the exported symbols belong to?
   - Is this a plugin/wrapper for another library (check symbol patterns)?
   - Consider: filename might be misleading, symbols don't lie
   - Does this binary come from a specific open-source project or library?
   - If no clear evidence found through search/knowledge base → report as None
   - Custom/demo applications typically have no identifiable source library

3. ARCHITECTURE PATTERN RECOGNITION:
   - Plugin architecture: Look for *_plugin_* patterns in symbols
   - Client library: Look for consistent API prefixes
   - Wrapper library: Mixed symbol patterns from different sources

4. CONTEXT VALIDATION:
   {"- Validate findings against the provided software context" if software_context else "- Use general software knowledge for validation"}
   - Ensure identified purpose aligns with deployment environment
   - Check consistency with expected technology patterns

CRITICAL ANALYSIS PRIORITY:
1. Exported symbols (highest priority - these reveal true identity)
2. Imported symbols (show dependencies and usage patterns)
3. Filename and path (can be misleading, use for validation only)
4. Context and external knowledge

CRITICAL: Only populate 'source_library' when confident about the primary source project.
Trust symbol evidence over naming conventions. If uncertain, leave it null.

FOCUS: This is rapid external identification with symbol-based evidence priority.
"""

        return prompt