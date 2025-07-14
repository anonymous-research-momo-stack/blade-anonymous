from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

from app.config import settings
from app.interface import TargetBinary
from app.tpl_detection.agent_analysis.response_models import BinaryInformation
from app.tpl_detection.agent_analysis.model_factory import create_model
from agno.tools.duckduckgo import DuckDuckGoTools


class BinaryInformationFinder:
    def __init__(self,
                 knowledge_json_path: str = None,
                 enable_web_search: bool = True,
                 enable_knowledge_base: bool = True):

        # 构建工具列表
        tools = []
        if enable_web_search:
            tools.append(DuckDuckGoTools())

        # 构建知识库
        knowledge = None
        if enable_knowledge_base:
            if knowledge_json_path is None:
                raise ValueError("knowledge_json_path is required when enable_knowledge_base=True")

            knowledge = JSONKnowledgeBase(
                path=knowledge_json_path,
                vector_db=PgVector(
                    table_name="json_documents",
                    db_url=settings.KNOWLEDGE_DATABASE_URL,
                    search_type=SearchType.hybrid  # Hybrid Search
                ),
            )

        # 构建instructions
        instructions = [
            "You are a binary analysis specialist focused on identifying the primary source and composition of binary files.",

            "CORE MISSION: Determine what this binary file IS and identify its primary source library/project.",
            "This analysis is CRITICAL for subsequent library composition analysis.",

            "KEY IDENTIFICATION TASKS:",
            "1. Binary Identity: What is this binary file (executable, library, tool, etc.)?",
            "2. Primary Function: What is its main purpose and functionality?",
            "3. Source Library: Does this binary come from a specific library/project whose code it contains?",

            "SOURCE LIBRARY IDENTIFICATION PRINCIPLES:",
            "- If binary name matches a known library (e.g., 'openssl' binary → OpenSSL library), this is strong evidence",
            "- If binary is a library file (e.g., 'libssl.a'), identify which project it comes from",
            "- If binary appears to be compiled from a specific open-source project, identify that project",
            "- Only identify source library when there's clear evidence of the relationship",

            "CRITICAL EXAMPLES:",
            "✅ Binary 'openssl' → Source Library: OpenSSL (binary IS the OpenSSL toolkit)",
            "✅ Binary 'libssl.a' → Source Library: OpenSSL (libssl is part of OpenSSL project)",
            "✅ Binary 'libcrypto.so' → Source Library: OpenSSL (libcrypto is OpenSSL's crypto library)",
            "✅ Binary 'nginx' → Source Library: Nginx (binary IS the nginx web server)",
            "✅ Binary 'sqlite3' → Source Library: SQLite (binary IS the SQLite tool)",
            "❓ Binary 'myapp' → Source Library: Only if clear evidence points to a specific project",

            "ANALYSIS APPROACH:",
            "- Use binary name patterns and known software projects",
            "- Consider file naming conventions (lib prefix, common tool names)",
            "- Look for obvious matches between binary names and well-known projects",
            "- Be conservative: only identify source library when confident",

            "SOURCE LIBRARY CRITERIA:",
            "- Must be a real, identifiable open-source project or library",
            "- Must have a reasonable connection to the binary file",
            "- Should represent the primary codebase that this binary is built from",
            "- Avoid guessing - better to leave null if uncertain",
        ]

        # 根据开关状态添加搜索相关指令
        if enable_knowledge_base or enable_web_search:
            instructions.append("VERIFICATION RESOURCES:")

        if enable_web_search:
            instructions.append("- Search online to verify binary identity and source project relationships")

        if enable_knowledge_base:
            instructions.append("- Consult knowledge base for known binary-to-library mappings")

        instructions.extend([
            "- Always provide your assessment with clear confidence indicators",
            "- Focus on providing actionable information for library composition analysis",
            "",
            "RESPONSE REQUIREMENTS:",
            "- Binary name: Normalized name of the binary",
            "- Description: Comprehensive but focused description covering identity, purpose, and context",
            "- Source library: Only when confident about the primary source project (can be null)",
            "",
            "This analysis establishes the foundation for identifying all libraries whose code is present in the binary."
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

        # 只有在知识库存在时才加载
        if knowledge is not None:
            self.agent.knowledge.load(recreate=False)

    def find_for(self, target_binary: TargetBinary):
        """
        Analyze binary file to identify its primary source and composition context

        :param target_binary: Target binary to analyze
        :return: response containing binary information
        """

        task_prompt = f"""Analyze this binary file to establish the foundation for library composition analysis:

BINARY DETAILS:
- Name: {target_binary.binary_name}
- Size: {target_binary.file_size_kb} KB
- Path: {target_binary.relative_path}

ANALYSIS REQUIREMENTS:

1. BINARY IDENTITY ANALYSIS:
   - What type of binary is this? (executable, static library, shared library, etc.)
   - What is its primary function and purpose?
   - What category of software does it belong to?

2. SOURCE LIBRARY IDENTIFICATION:
   - Does this binary come from a specific open-source project or library?
   - Is there a clear relationship between the binary name and a known library/project?
   - Examples of clear relationships:
     * 'openssl' binary → OpenSSL project
     * 'libssl.a' library → OpenSSL project  
     * 'nginx' binary → Nginx project
     * 'sqlite3' binary → SQLite project

3. COMPOSITION ANALYSIS CONTEXT:
   - What types of libraries would reasonably be included in this binary?
   - Any specific technical domains this binary operates in?
   - Security considerations or notable characteristics?

CRITICAL: The 'source_library' field should only be populated when you can confidently identify the primary open-source project that this binary is built from or belongs to. If uncertain, leave it null.

CONFIDENCE INDICATORS: Clearly indicate your confidence level in the identification, especially for the source library determination.

This analysis will guide subsequent steps that identify all libraries whose code is present in this binary."""

        response = self.agent.run(task_prompt)

        binary_info = response.content

        target_binary.information = binary_info

        return response