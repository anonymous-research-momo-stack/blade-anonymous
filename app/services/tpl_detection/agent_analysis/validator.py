import time
import traceback
from collections import Counter
from typing import List, Dict
from loguru import logger

from agno.agent import Agent
from agno.knowledge.json import JSONKnowledgeBase
from agno.run.response import RunResponse
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

from app.config import settings
from app.interface import TargetBinary, Library
from app.services.tpl_detection.agent_analysis.response_models import IndividualValidationResults, RedundancyAnalysisResult, \
    RedundancyAnalysisResults, SoftwareContext
from app.services.tpl_detection.agent_analysis.model_factory import create_model
from agno.tools.duckduckgo import DuckDuckGoTools


class LibraryValidator:
    """
    Expert Library Validator - STEP 3: Binary Composition Analysis
    专业库验证器：智能二进制组成分析的最终验证环节
    """

    def __init__(self,
                 knowledge_json_path: str = None,
                 enable_web_search: bool = True,
                 enable_knowledge_base: bool = False,
                 enable_db_verification: bool = True):

        self.enable_db_verification = enable_db_verification


        # Build tools list
        tools = []
        if enable_web_search:
            tools.append(DuckDuckGoTools())

        # Build knowledge base
        knowledge = None
        if enable_knowledge_base and knowledge_json_path:
            knowledge = JSONKnowledgeBase(
                path=knowledge_json_path,
                vector_db=PgVector(
                    table_name="library_validation_documents",
                    db_url=settings.KNOWLEDGE_DATABASE_URL,
                    search_type=SearchType.hybrid
                ),
            )

        # 专家级验证指令系统 - 完全重构
        expert_instructions = [
            "You are a senior binary composition analysis expert conducting the final validation phase.",
            "",
            "WORKFLOW CONTEXT:",
            "This is STEP 3 (FINAL) of a 3-step binary composition analysis workflow:",
            "• STEP 1 (completed): Binary identity analysis → identified primary source library",
            "• STEP 2 (completed): Library discovery → found candidate libraries using feature matching + agent analysis",
            "• STEP 3 (your role): Expert validation → verify and refine the candidate library list",
            "",
            "MISSION: Validate which candidate libraries actually have SOURCE CODE compiled into this binary",
            "",
            "CORE EXPERTISE DOMAINS:",
            "- Software architecture patterns and typical dependency relationships",
            "- Library ecosystem knowledge and inter-library relationships",
            "- Binary composition analysis and evidence evaluation",
            "- Distinguishing code inclusion from API usage and false positives",
            "",
            "VALIDATION FRAMEWORK:",
            "You will conduct a two-step expert validation process:",
            "1. INDIVIDUAL LIBRARY VALIDATION: Assess each candidate for source code inclusion likelihood",
            "2. CONFLICT RESOLUTION: Resolve contradictions and eliminate redundancy",
            "",
            "STEP 1: SOURCE CODE INCLUSION VALIDATION",
            "",
            "For each candidate library, evaluate these critical dimensions:",
            "",
            "A. PRIMARY SOURCE LIBRARY STATUS (HIGHEST PRIORITY)",
            "- If a library was identified as the 'primary source' in Step 1, it gets special status",
            "- Primary source libraries should have high confidence unless strong contrary evidence exists",
            "- Examples: 'openssl' binary → OpenSSL is primary source (very high confidence)",
            "",
            "B. EVIDENCE STRENGTH ASSESSMENT",
            "- STRONG evidence: Copyright/license statements, version strings, project URLs, library-specific function signatures",
            "- MEDIUM evidence: Function prefixes, library-related patterns, build paths, configuration strings",
            "- WEAK evidence: Generic function names, common terminology, shared patterns",
            "",
            "C. FUNCTIONAL RELATIONSHIP ANALYSIS (CRITICAL)",
            "",
            "REASONABLE functional relationships:",
            "✓ Functional identity: Binary IS the library implementation (e.g., openssl binary ← OpenSSL library)",
            "✓ Forward dependency: Upper-layer application depends on lower-layer library (e.g., web server ← OpenSSL)",
            "",
            "UNREASONABLE patterns (RED FLAGS):",
            "❌ REVERSE DEPENDENCY ERROR: Lower-layer library containing upper-layer application code",
            "   Examples: libpng containing OpenCV code, zlib containing nginx code, OpenSSL containing Apache code",
            "   Rule: Infrastructure libraries should NOT contain application-layer code",
            "",
            "❌ FUNCTIONAL DOMAIN MISMATCH: Completely unrelated functionality domains",
            "   Examples: SSL tools containing 3D modeling libraries, database tools containing audio processing",
            "",
            "❌ GENERIC STRING CONFUSION: Matches based only on common programming terms",
            "   Examples: Matches only on 'error', 'init', 'free', standard C library functions",
            "",
            "❌ API CALL CONFUSION: Mistaking API usage for code inclusion",
            "   Examples: Detecting SSL_connect calls and assuming OpenSSL code inclusion (might just be API usage)",
            "",
            "❌ COMPETING LIBRARY COEXISTENCE: Multiple libraries serving identical functions",
            "   Examples: OpenSSL + BoringSSL, zlib + lz4, libxml2 + expat simultaneously",
            "",
            "❌ VERSION/BRANCH CONFLICTS: Same library, different versions simultaneously",
            "   Examples: OpenSSL 1.1 + OpenSSL 3.0, different branches of same library",
            "",
            "D. ARCHITECTURAL REASONABLENESS",
            "- Would this library realistically be statically compiled into this binary?",
            "- Does the inclusion make sense from software engineering perspective?",
            "- Consider typical development and deployment patterns",
            "",
            "STEP 2: CONFLICT RESOLUTION AND REDUNDANCY ELIMINATION",
            "",
            "Systematically resolve conflicts using this priority framework:",
            "",
            "PRIORITY LEVELS:",
            "1. PRIMARY SOURCE LIBRARY (from Step 1) - Highest protection",
            "2. Strong evidence + perfect functional fit",
            "3. Medium evidence + reasonable functional relationship",
            "4. Weak evidence candidates",
            "",
            "CONFLICT RESOLUTION STRATEGIES:",
            "",
            "A. FUNCTIONAL CONFLICTS (mutually exclusive)",
            "- Competing implementations (OpenSSL vs BoringSSL) → Keep the one with stronger evidence/better fit",
            "- Same-function libraries (zlib vs lz4) → Keep the most appropriate one",
            "",
            "B. INCLUSION RELATIONSHIPS (parent/child)",
            "- Parent library vs sub-components (OpenSSL vs libcrypto/libssl) → Keep parent only",
            "- Framework vs modules → Keep framework, remove individual modules",
            "",
            "C. VERSION CONFLICTS",
            "- Same library, different versions → Keep the one with stronger evidence",
            "- Same library, different detection methods → Merge evidence, keep one entry",
            "",
            "D. EVIDENCE QUALITY CONFLICTS",
            "- Strong evidence library vs weak evidence library serving same function → Keep strong evidence",
            "",
            "PROFESSIONAL STANDARDS:",
            "- Every decision must be backed by clear technical reasoning",
            "- Demonstrate deep understanding of software architecture principles",
            "- Provide confident, authoritative assessments suitable for technical stakeholders",
            "- Use professional terminology and systematic analysis approach",
            "",
            "QUALITY ASSURANCE:",
            "- Primary source library should be preserved unless compelling contrary evidence",
            "- Final result should be architecturally consistent and conflict-free",
            "- Each included library should have credible evidence of source code inclusion",
            "- Provide clear reasoning for every validation decision"
        ]

        if enable_knowledge_base or enable_web_search:
            expert_instructions.append(
                "RESEARCH RESOURCES: Leverage available tools for verification and enhanced analysis quality.")

        self.agent = Agent(
            model=create_model(),
            tools=tools,
            show_tool_calls=True,
            knowledge=knowledge,
            search_knowledge=enable_knowledge_base,
            instructions=expert_instructions
        )

        # Load knowledge base if exists
        if knowledge is not None:
            self.agent.knowledge.load(recreate=False)

    def validate_libraries(self,
                           libraries: List[Library],
                           target_binary: TargetBinary,
                           context:SoftwareContext=None) -> (List[Library], Dict):
        """
        Expert two-step validation workflow
        """
        if not libraries:
            return [], {}

        logger.debug(f"\n=== EXPERT VALIDATION WORKFLOW - {target_binary.binary_name} ===")
        logger.debug(f"Validating {len(libraries)} candidate libraries through two-step expert analysis")

        # TODO 记录这三个小步骤的时间
        # 预处理和特征分析
        start_at = time.perf_counter()
        enhanced_libraries = self._enhance_libraries_with_analysis(libraries, target_binary)
        validate_enhance_duration = time.perf_counter() - start_at

        try:
            step_1_start_at = time.perf_counter()
            # 第一步：源代码包含合理性验证
            logger.debug(f"\n--- STEP 1: SOURCE CODE INCLUSION VALIDATION ---")
            individual_results, step_1_response = self._step1_source_code_inclusion_validation(enhanced_libraries,
                                                                                               target_binary,
                                                                                               context)
            # 更新 library 属性
            reasonable_libs = []
            for lib in enhanced_libraries:
                for result in individual_results.results:
                    # 找到对应的分析结果
                    if result.library_name.lower() == lib.name.lower():
                        # 标记是否合理
                        lib.is_reasonable = result.is_reasonable
                        lib.reasonable_reasoning = result.reasoning
                        if result.is_reasonable:
                            lib.validation_passed = True # 默认通过
                            reasonable_libs.append(lib)

            logger.debug(
                f"Source code inclusion assessment: {len(reasonable_libs)}/{len(enhanced_libraries)} libraries validated")
            step_1_duration = time.perf_counter() - step_1_start_at

            step_2_start_at = time.perf_counter()
            # 第二步：冲突解决和冗余消除
            logger.debug(f"\n--- STEP 2: CONFLICT RESOLUTION AND REDUNDANCY ELIMINATION ---")
            if len(reasonable_libs) <= 1:
                # 只有一个或没有合理库，跳过冲突解决
                redundancy_results = RedundancyAnalysisResults(results=[
                    RedundancyAnalysisResult(
                        library_name=lib.name,
                        should_keep=True,
                        reasoning="Only validated library, no conflicts to resolve."
                    ) for lib in reasonable_libs
                ])
                step_2_response = None
            else:
                redundancy_results, step_2_response = self._step2_conflict_resolution(reasonable_libs, target_binary,context)

            # 应用最终验证结果
            validated_libraries = self._apply_expert_validation_results(individual_results, redundancy_results,
                                                                        enhanced_libraries)

            step_2_duration = time.perf_counter() - step_2_start_at
            process_data = {
                "step_1_response": step_1_response,
                "individual_results": individual_results.results,
                "step_2_response": step_2_response,
                "redundancy_results": redundancy_results.results,
                "duration": {
                    "__validation_enhance": validate_enhance_duration,
                    "__validation_step_1": step_1_duration,
                    "__validation_step_2": step_2_duration
                }
            }

            return validated_libraries, process_data

        except Exception as e:
            logger.error(f"Expert validation failed with error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            # 返回原始库列表，标记为未验证
            for lib in libraries:
                lib.validation_passed = False
                lib.validation_reasoning = f"Validation failed due to error: {str(e)}"
            return libraries, {}

    def _enhance_libraries_with_analysis(self,
                                         libraries: List[Library],
                                         target_binary: TargetBinary) -> List[Library]:
        """增强库信息：特征分析和数据库补充"""
        # 基础增强
        enhanced_libraries = self._enhance_libraries_with_db_features(libraries, target_binary)

        # 特征独特性分析
        enhanced_libraries = self._analyze_feature_uniqueness(enhanced_libraries)

        return enhanced_libraries

    def _enhance_libraries_with_db_features(self,
                                            libraries: List[Library],
                                            target_binary: TargetBinary) -> List[Library]:
        """为Agent分析结果补充数据库特征匹配信息"""
        if not self.enable_db_verification:
            return libraries

        enhanced_libraries = []
        for library in libraries:
            enhanced_lib = Library(
                name=library.name,
                id=library.id,
                description=library.description,
                identify_methods=library.identify_methods[:],
                matched_strings=library.matched_strings[:],
                evidence_type=library.evidence_type,
                evidences=library.evidences[:] if library.evidences else [],
                reasoning=library.reasoning
            )

            # 简化的数据库查询
            if ("Agent" in library.identify_methods and
                    len(library.matched_strings) == 0):
                try:
                    db_match_count = self._query_db_feature_match(library.name, target_binary.strings)
                    if db_match_count > 0:
                        enhanced_lib.matched_strings = [f"Database matches: {db_match_count}"]
                        enhanced_lib.identify_methods.append("Database Verification")
                except Exception as e:
                    logger.error(f"Database feature match query failed for library '{library.name}': {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    pass

            enhanced_libraries.append(enhanced_lib)

        return enhanced_libraries

    def _analyze_feature_uniqueness(self, libraries: List[Library]) -> List[Library]:
        """分析每个库的特征独特性"""
        # 统计每个字符串被多少个库匹配
        string_counts = Counter()
        for lib in libraries:
            for string in lib.matched_strings:
                string_counts[string] += 1

        # 为每个库计算独特性信息
        for lib in libraries:
            if lib.matched_strings:
                unique_strings = [s for s in lib.matched_strings if string_counts[s] == 1]
                shared_strings = [s for s in lib.matched_strings if string_counts[s] > 1]

                # 添加独特性分析属性
                lib.unique_features = unique_strings
                lib.shared_features = shared_strings
                lib.uniqueness_score = len(unique_strings) / len(lib.matched_strings)
                lib.unique_feature_count = len(unique_strings)
                lib.shared_feature_count = len(shared_strings)
            else:
                lib.unique_features = []
                lib.shared_features = []
                lib.uniqueness_score = 0.0
                lib.unique_feature_count = 0
                lib.shared_feature_count = 0

        return libraries

    def _query_db_feature_match(self, library_name: str, binary_strings: List[str]) -> int:
        """查询数据库计算特征匹配数量"""
        if not self.enable_db_verification:
            return 0
        # TODO: 实现具体的数据库查询逻辑
        return 0

    def _step1_source_code_inclusion_validation(self, libraries: List[Library],
                                                target_binary: TargetBinary, software_context:SoftwareContext) -> (
    IndividualValidationResults, RunResponse):
        """第一步：源代码包含合理性验证"""

        # 设置响应模型
        self.agent.response_model = IndividualValidationResults

        prompt = self._build_step1_expert_prompt(libraries, target_binary,software_context)

        response = self.agent.run(prompt)
        return response.content, response

    def _build_step1_expert_prompt(self, libraries, target_binary, software_context:SoftwareContext):
        # 构建专家级验证prompt
        binary_context = self._build_comprehensive_binary_context(target_binary)
        validation_framework = self._get_detailed_validation_framework()

        prompt = f"""EXPERT BINARY COMPOSITION ANALYSIS - STEP 1: SOURCE CODE INCLUSION VALIDATION

{binary_context}

VALIDATION MISSION:
Conduct expert-level assessment of whether each candidate library's SOURCE CODE is realistically compiled into this binary.

{validation_framework}

CANDIDATE LIBRARIES FOR EXPERT VALIDATION ({len(libraries)}):
"""
        for i, lib in enumerate(libraries, 1):
            prompt += f"\n{i}. LIBRARY: {lib.name}"
            if lib.description:
                prompt += f"\n   Description: {lib.description[:150]}..."

            prompt += f"\n   Detection Methods: {', '.join(lib.identify_methods)}"

            # 特殊标记主体库
            is_primary_source = self._is_primary_source_library(lib, target_binary)
            if is_primary_source:
                prompt += f"\n   ⭐ PRIMARY SOURCE LIBRARY STATUS: This library was identified as the primary source in Step 1"

            # 包含特征独特性分析
            if hasattr(lib, 'unique_feature_count'):
                total_features = len(lib.matched_strings) if lib.matched_strings else 0
                prompt += f"\n   Evidence Profile: {total_features} total features"
                if total_features > 0:
                    prompt += f" ({lib.unique_feature_count} unique, {lib.shared_feature_count} shared)"

                    # 展示独特特征样例
                    if lib.unique_features:
                        unique_examples = lib.unique_features[:2]
                        prompt += f"\n   Key Unique Evidence: {', '.join(unique_examples)}"
                        if len(lib.unique_features) > 2:
                            prompt += f"... (+{len(lib.unique_features) - 2} more unique)"

                    # 展示一些证据类型
                    if hasattr(lib, 'evidences') and lib.evidences:
                        evidence_examples = lib.evidences[:2]
                        prompt += f"\n   Agent Evidence: {', '.join(evidence_examples)}"
                        if len(lib.evidences) > 2:
                            prompt += f"... (+{len(lib.evidences) - 2} more)"
            elif lib.matched_strings:
                match_count = len(lib.matched_strings)
                if match_count <= 2:
                    examples = ", ".join(lib.matched_strings)
                else:
                    examples = ", ".join(lib.matched_strings[:2]) + f"... (+{match_count - 2} more)"
                prompt += f"\n   Evidence ({match_count} features): {examples}"

            if lib.reasoning:
                prompt += f"\n   Original Analysis: {lib.reasoning[:200]}..."

            prompt += "\n"

        # 上下文
        if software_context:
            prompt += f"""
        SOFTWARE CONTEXT FOR INCLUSION VALIDATION:
        - Type: {software_context.software_type}
        - Purpose: {software_context.primary_purpose}
        - Environment: {software_context.deployment_environment}
        - Architecture: {software_context.architecture_pattern}

        CONTEXT-BASED INCLUSION ASSESSMENT:

        ARCHITECTURAL REASONABLENESS CHECK:
        - Does this library type typically appear in {software_context.software_type} applications?
        - Is the library scope appropriate for {software_context.deployment_environment} constraints?
        - Does the library functionality align with stated purpose: {software_context.primary_purpose}?

        DOMAIN-SPECIFIC VALIDATION:
        - Apply domain knowledge about typical library usage patterns
        - Consider environmental constraints (memory, processing power, real-time requirements)
        - Evaluate functional domain matching (crypto libs in security apps, graphics libs in games)

        EXAMPLES OF CONTEXT-GUIDED VALIDATION:
        - Graphics libraries in command-line tools → Suspicious, needs strong evidence
        - Real-time processing libraries in batch systems → Investigate architectural mismatch  
        - Heavy framework libraries in embedded systems → Verify resource constraints compatibility
        - Desktop UI libraries in server applications → Flag as potential false positive

        Use context to enhance your architectural reasonableness assessment, not to override evidence.
        """

        prompt += f"""
EXPERT VALIDATION REQUIREMENTS:

For each library, conduct systematic expert analysis covering:

1. PRIMARY SOURCE ASSESSMENT:
   - If marked as primary source library, explain why it should be validated or rejected
   - Primary source libraries require strong contrary evidence for rejection

2. EVIDENCE STRENGTH EVALUATION:
   - Assess the quality and reliability of detection evidence
   - Distinguish strong evidence (copyright, library-specific signatures) from weak evidence (generic patterns)

3. FUNCTIONAL RELATIONSHIP ANALYSIS:
   - Evaluate functional consistency between library and binary
   - CRITICAL: Check for reverse dependency errors (infrastructure library containing application code)
   - Identify any domain mismatches or architectural inconsistencies

4. SOURCE CODE INCLUSION LIKELIHOOD:
   - Professional assessment of whether this library's code would realistically be compiled into this binary
   - Consider typical software architecture patterns and development practices

VALIDATION DECISION FRAMEWORK:
- is_reasonable: true/false based on comprehensive evidence assessment
- confidence: HIGH (strong evidence + perfect fit), MEDIUM (good evidence + reasonable fit), LOW (weak evidence or concerns)
- reasoning: Expert-level technical analysis demonstrating systematic evaluation

PROFESSIONAL STANDARDS: Provide authoritative, well-reasoned assessments suitable for technical stakeholders.
"""
        return prompt

    def _step2_conflict_resolution(self, reasonable_libraries: List[Library],
                                   target_binary: TargetBinary, software_context:SoftwareContext) -> (RedundancyAnalysisResults, RunResponse):
        """第二步：冲突解决和冗余消除"""

        # 设置结构化响应模型
        self.agent.response_model = RedundancyAnalysisResults

        prompt = self._build_step2_expert_prompt(reasonable_libraries, target_binary,software_context)


        response = self.agent.run(prompt)
        return response.content, response

    def _build_step2_expert_prompt(self, reasonable_libraries, target_binary, software_context:SoftwareContext):
        binary_context = self._get_comprehensive_binary_context(target_binary)
        conflict_framework = self._get_conflict_resolution_framework()

        prompt = f"""EXPERT BINARY COMPOSITION ANALYSIS - STEP 2: CONFLICT RESOLUTION & REDUNDANCY ELIMINATION

{binary_context}

VALIDATED LIBRARIES FROM STEP 1 ({len(reasonable_libraries)}):
"""
        # 识别主体库
        primary_libs = []
        other_libs = []

        for lib in reasonable_libraries:
            if self._is_primary_source_library(lib, target_binary):
                primary_libs.append(lib)
            else:
                other_libs.append(lib)

        if primary_libs:
            prompt += f"\nPRIMARY SOURCE LIBRARIES ({len(primary_libs)} - Highest Priority):\n"
            for i, lib in enumerate(primary_libs, 1):
                prompt += f"{i}. {lib.name}"
                if lib.description:
                    prompt += f" - {lib.description[:100]}..."
                prompt += f"\n   Evidence: {len(lib.matched_strings)} features" if lib.matched_strings else ""
                prompt += f", Methods: {', '.join(lib.identify_methods)}\n"

        if other_libs:
            prompt += f"\nOTHER VALIDATED LIBRARIES ({len(other_libs)}):\n"
            for i, lib in enumerate(other_libs, 1):
                prompt += f"{i}. {lib.name}"
                if lib.description:
                    prompt += f" - {lib.description[:100]}..."
                prompt += f"\n   Evidence: {len(lib.matched_strings)} features" if lib.matched_strings else ""
                if hasattr(lib, 'uniqueness_score'):
                    prompt += f", Uniqueness: {lib.uniqueness_score:.1%}"
                prompt += f", Methods: {', '.join(lib.identify_methods)}\n"
        if software_context:
            prompt += f"""
CONTEXT-DRIVEN CONFLICT RESOLUTION:

SOFTWARE CONTEXT:
- Type: {software_context.software_type}
- Environment: {software_context.deployment_environment}
- Purpose: {software_context.primary_purpose}
- Build System: {software_context.build_system}

CONTEXT-BASED PRIORITY FRAMEWORK:

1. ENVIRONMENTAL OPTIMIZATION:
   - In resource-constrained environments: prefer lightweight over feature-rich
   - In performance-critical systems: prefer optimized over generic implementations
   - In embedded systems: prefer deterministic over dynamic libraries

2. ARCHITECTURAL PATTERN ALIGNMENT:
   - Microservices: prefer focused, single-purpose libraries
   - Monolithic: can accommodate comprehensive, multi-feature libraries
   - Real-time systems: prefer predictable performance libraries

3. DOMAIN-TYPICAL PREFERENCES:
   - Consider what libraries are commonly chosen in this domain
   - Factor in industry standards and best practices
   - Account for compliance and certification requirements

CONFLICT RESOLUTION WITH CONTEXT:
When multiple libraries serve similar functions with comparable evidence:
1. Apply primary evidence-based hierarchy first
2. Use context to assess architectural appropriateness as tie-breaker
3. Consider domain-specific optimization and compliance factors
4. Prefer libraries that match the system's complexity and scale requirements

CONTEXT APPLICATION EXAMPLES:
- Embedded automotive: Memory-efficient crypto > Feature-complete crypto
- Web backend: Scalable database > Embedded database  
- Real-time system: Deterministic timing > General-purpose libraries
- Mobile app: Battery-optimized > Server-optimized libraries

Context guides decision-making but never overrides strong technical evidence.
        """
        prompt += f"""
{conflict_framework}

CONFLICT RESOLUTION MISSION:
Systematically identify and resolve conflicts to produce a clean, architecturally consistent final library list.

CRITICAL ANALYSIS AREAS:

1. FUNCTIONAL CONFLICTS:
   - Identify competing implementations (e.g., OpenSSL vs BoringSSL)
   - Detect same-function libraries that shouldn't coexist
   - Apply priority-based resolution

2. INCLUSION RELATIONSHIPS:
   - Identify parent-child relationships (e.g., OpenSSL parent vs libssl/libcrypto components)
   - Consolidate to parent libraries only

3. VERSION/DETECTION CONFLICTS:
   - Detect same library identified through different methods
   - Merge evidence and consolidate to single entry

4. PRIORITY-BASED RESOLUTION:
   - Primary source libraries get highest protection
   - Strong evidence libraries preferred over weak evidence
   - Better architectural fit preferred

5. NAMING VARIANT CONFLICTS:
   - Identify same projects detected with different name formats (e.g., postgres vs PostgreSQL)
   - Apply priority resolution: Feature matching method > Repository name proximity > Generic names
   - Consolidate to single best representation
   
CONFLICT RESOLUTION RULES:
- PRIMARY SOURCE LIBRARIES: Preserve unless compelling technical reasons for removal
- COMPETING FUNCTIONS: Keep only the best-supported implementation
- PARENT-CHILD: Keep parent library, remove child components
- EVIDENCE CONFLICTS: Prefer stronger evidence and better architectural fit
- NAMING VARIANTS: Keep one representation per project using priority hierarchy

SPECIAL ATTENTION - NAMING VARIANT DETECTION:
Pay special attention to libraries that represent the same project but with different naming conventions:
- Examples: "postgres" vs "PostgreSQL", "openssl" vs "OpenSSL", "sqlite" vs "SQLite"
- These should be treated as redundant variants of the same library
- Resolution priority: 
  1. Libraries detected via feature matching methods (strongest evidence)
  2. Names closer to official source repository names
  3. Other naming variants
- When consolidating, preserve the highest-priority variant and remove others as redundant

OUTPUT REQUIREMENT:
For each library, decide should_keep (true/false) with professional reasoning explaining the decision.
Ensure final result is conflict-free and architecturally sound.
"""
        return prompt

    def _build_comprehensive_binary_context(self, target_binary: TargetBinary) -> str:
        """构建全面的二进制上下文信息"""
        context = f"""BINARY ANALYSIS CONTEXT:
- Target: {target_binary.binary_name}
- Size: {target_binary.file_size_kb} KB
- Path: {target_binary.relative_path}
"""

        if target_binary.information:
            context += f"- Type/Purpose: {target_binary.information.description}\n"
            if target_binary.information.source_library:
                context += f"- Primary Source Library: {target_binary.information.source_library.name}\n"
                context += f"  Description: {target_binary.information.source_library.description}\n"

        if target_binary.dynamic_libraries:
            context += f"- External Dependencies: {len(target_binary.dynamic_libraries)} dynamic libraries (excluded from analysis)\n"

        return context

    def _get_detailed_validation_framework(self) -> str:
        """获取详细的验证框架说明"""
        return """
EXPERT VALIDATION FRAMEWORK:

PRIMARY SOURCE LIBRARY SPECIAL STATUS:
- Libraries identified as "primary source" in Step 1 get highest validation priority
- Requires strong contrary evidence for rejection
- Represents the main codebase this binary is built from

EVIDENCE STRENGTH CLASSIFICATION:
- STRONG: Copyright/license statements, version declarations, project URLs, library-unique function signatures
- MEDIUM: Function prefixes, library-related configurations, build paths, error messages
- WEAK: Generic function names, common programming terms, shared patterns

FUNCTIONAL RELATIONSHIP VALIDATION:
✓ VALID RELATIONSHIPS:
  • Functional identity: Binary IS the library (openssl binary ← OpenSSL library)
  • Forward dependency: Application uses infrastructure library (web server ← OpenSSL)

❌ INVALID PATTERNS (REJECT):
  • Reverse dependency: Infrastructure library containing application code (libpng ← OpenCV)
  • Domain mismatch: Unrelated functionality (SSL tool ← 3D modeling library)
  • Generic confusion: Matches only on common terms (error, init, free)
  • API confusion: API calls mistaken for code inclusion
  • Competing coexistence: Multiple libraries for same function (OpenSSL + BoringSSL)
  • Version conflicts: Same library, multiple versions

ARCHITECTURAL REASONABLENESS ASSESSMENT:
- Would this library realistically be statically compiled into this binary?
- Does the inclusion align with typical software engineering practices?
- Consider build patterns, deployment strategies, and dependency management
"""

    def _get_conflict_resolution_framework(self) -> str:
        """获取冲突解决框架"""
        return """
CONFLICT RESOLUTION FRAMEWORK:

PRIORITY HIERARCHY:
1. PRIMARY SOURCE LIBRARIES (Highest Protection)
2. Strong Evidence + Perfect Functional Fit
3. Medium Evidence + Reasonable Relationship
4. Weak Evidence Candidates

SYSTEMATIC CONFLICT TYPES:

A. FUNCTIONAL CONFLICTS (Mutually Exclusive):
   - Competing SSL implementations: OpenSSL vs BoringSSL vs WolfSSL
   - Competing compression: zlib vs lz4 vs bzip2
   - Competing XML parsers: libxml2 vs expat
   Resolution: Keep strongest evidence + best architectural fit

B. INCLUSION RELATIONSHIPS (Parent/Child):
   - OpenSSL project: Keep "OpenSSL", remove "libssl", "libcrypto"
   - Framework components: Keep framework, remove individual modules
   Resolution: Consolidate to parent library

C. VERSION/BRANCH CONFLICTS:
   - Same library, different versions: OpenSSL 1.1 vs OpenSSL 3.0
   - Same library, different detection methods: Feature matching vs Agent analysis
   Resolution: Merge evidence, keep single best-supported version

D. EVIDENCE QUALITY CONFLICTS:
   - Strong evidence library vs weak evidence library (same function)
   Resolution: Prefer strong evidence library

E. NAMING VARIANTS (Same Project, Different Names):
   - Same project with different name formats: postgres vs PostgreSQL, openssl vs OpenSSL
   - Official vs abbreviated names: JavaScript vs JS, GNU Compiler Collection vs GCC
   Resolution Priority: Feature matching detection > Source repository name proximity > Other names
"""

    def _get_comprehensive_binary_context(self, target_binary: TargetBinary) -> str:
        """获取全面的二进制上下文"""
        context = f"""CONFLICT RESOLUTION CONTEXT:
Binary: {target_binary.binary_name} ({target_binary.file_size_kb} KB)
"""
        if target_binary.information:
            context += f"Purpose: {target_binary.information.description[:200]}...\n"
            if target_binary.information.source_library:
                context += f"Primary Source: {target_binary.information.source_library.name}\n"
        context += "Mission: Eliminate conflicts while preserving all legitimate libraries with source code inclusion."
        return context

    def _is_primary_source_library(self, lib: Library, target_binary: TargetBinary) -> bool:
        """检查是否为主体源库"""
        if not target_binary.information or not target_binary.information.source_library:
            return False

        primary_name = target_binary.information.source_library.name.lower()
        lib_name = lib.name.lower()

        # 精确匹配或包含关系
        return lib_name == primary_name or primary_name in lib_name or lib_name in primary_name

    def _is_library_reasonable(self, library_name: str, individual_results: IndividualValidationResults) -> bool:
        """检查库是否通过个体合理性检查"""
        for result in individual_results.results:
            if result.library_name.lower() == library_name.lower():
                return result.is_reasonable
        return False

    def _apply_expert_validation_results(self,
                                         individual_results: IndividualValidationResults,
                                         redundancy_results: RedundancyAnalysisResults,
                                         libraries: List[Library]) -> List[Library]:
        """应用专家验证结果到库对象"""

        logger.debug(f"\n=== APPLYING EXPERT VALIDATION RESULTS ===")

        # 创建结果映射
        individual_map = {result.library_name: result for result in individual_results.results}
        redundancy_map = {result.library_name: result for result in redundancy_results.results}

        logger.debug(f"Individual validation results: {len(individual_map)} libraries")
        logger.debug(f"Conflict resolution results: {len(redundancy_map)} libraries")

        # 应用验证结果
        for lib in libraries:
            logger.debug(f"\nProcessing library: {lib.name}")

            # 查找个体验证结果（大小写不敏感）
            individual_result = self._find_result_case_insensitive(lib.name, individual_map)

            if individual_result:
                if not individual_result.is_reasonable:
                    # 个体验证失败
                    lib.validation_passed = False
                    lib.validation_reasoning = f"EXPERT REJECTION: {individual_result.reasoning}"
                    logger.debug(f"❌ {lib.name}: FAILED source code inclusion validation")
                else:
                    # 个体验证通过，检查冲突解决结果
                    redundancy_result = self._find_result_case_insensitive(lib.name, redundancy_map)

                    if redundancy_result:
                        lib.validation_passed = redundancy_result.should_keep

                        if redundancy_result.should_keep:
                            lib.is_redundant = False
                            lib.redundancy_reasoning =  f"EXPERT VALIDATION PASSED: {individual_result.reasoning}"
                            logger.debug(f"✅ {lib.name}: FULLY VALIDATED")
                        else:
                            lib.is_redundant = True
                            lib.redundancy_reasoning = f"CONFLICT RESOLUTION: {redundancy_result.reasoning}"
                            logger.debug(f"❌ {lib.name}: REMOVED in conflict resolution")
                    else:
                        # 个体通过但没有冲突检查（单一库情况）, 默认通过
                        lib.is_redundant = False
                        lib.validation_passed = True
                        lib.redundancy_reasoning = f"EXPERT VALIDATION PASSED: {individual_result.reasoning}"
                        logger.debug(f"✅ {lib.name}: VALIDATED (no conflicts to resolve)")
            else:
                # 没有验证结果，默认失败
                lib.is_redundant = True
                lib.validation_passed = False
                lib.redundancy_reasoning = "VALIDATION ERROR: No expert assessment available"
                logger.debug(f"❌ {lib.name}: Missing validation data")

        # 验证主体库保护
        self._verify_primary_source_protection(libraries)

        # 最终统计
        passed = sum(1 for lib in libraries if lib.validation_passed)
        failed = len(libraries) - passed
        logger.debug(f"\nEXPERT VALIDATION COMPLETE: {passed} LIBRARIES VALIDATED, {failed} REJECTED")

        return libraries

    def _verify_primary_source_protection(self, libraries: List[Library]):
        """验证主体库是否得到适当保护"""
        primary_libs = [lib for lib in libraries if hasattr(lib, 'is_primary_source') and lib.is_primary_source]
        if primary_libs:
            for lib in primary_libs:
                if not lib.validation_passed:
                    logger.debug(
                        f"⚠️  WARNING: Primary source library {lib.name} was rejected: {lib.validation_reasoning}")
                else:
                    logger.debug(f"✓ Primary source library {lib.name} protected and validated")
        else:
            logger.debug("ℹ️  No primary source libraries identified for protection")

    def _find_result_case_insensitive(self, library_name: str, result_map: Dict) -> any:
        """大小写不敏感地查找验证结果"""
        # 先尝试精确匹配
        if library_name in result_map:
            return result_map[library_name]

        # 大小写不敏感匹配
        for key, result in result_map.items():
            if key.lower() == library_name.lower():
                return result

        return None