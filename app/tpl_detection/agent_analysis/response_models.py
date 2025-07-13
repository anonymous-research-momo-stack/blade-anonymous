from typing import Optional, List

from pydantic import BaseModel, Field

# bin info finder
class LibraryInformation(BaseModel):
    """
    Agent answer format for library information
    """
    name: str = Field(
        description="The name of the third-party library."
    )
    description: str = Field(
        description="A concise description of the third-party library."
    )

# bin info finder
class BinaryInformation(BaseModel):
    """
    Agent answer format for binary analysis
    """
    name: str = Field(
        description="The name of this binary."
    )
    description: str = Field(
        description="Comprehensive description of the binary, including what it is, its main function, common use cases, security considerations, and any other useful information about this binary."
    )
    source_library: Optional[LibraryInformation] = Field(
        default=None,
        description="Information about the library or framework that may have compiled or generated this binary (if applicable)."
    )

# tpl analyzer
class LibraryResult(BaseModel):
    """
    Agent response model for library analysis
    """
    name: str = Field(description="Library name - use simple, recognizable names (prefer repository/package names)")
    description: str = Field(
        description="Brief description, include full name if different from name, mention repository if known")
    evidence_type: str = Field(description="Evidence type: Explicit, Implicit, or Mixed")
    evidences: List[str] = Field(description="Actual evidence strings from the binary that support this identification")
    reasoning: str = Field(
        description="Explanation of what specific evidence indicates this library's code is present in the binary")

# tpl analyzer
class TPLAnalysisResult(BaseModel):
    """
    Agent response model for complete TPL analysis
    """
    libraries: List[LibraryResult] = Field(description="List of identified third-party libraries")

# validator
class LibraryValidationResult(BaseModel):
    """个体库验证结果"""
    library_name: str = Field(description="Library name exactly as provided")
    is_reasonable: bool = Field(description="Whether this library could reasonably be compiled into the binary")
    reasoning: str = Field(description="Professional multi-dimensional analysis explaining the decision")
    confidence: str = Field(description="HIGH/MEDIUM/LOW confidence level")

# validator
class IndividualValidationResults(BaseModel):
    """第一步个体验证结果"""
    results: List[LibraryValidationResult] = Field(description="Individual validation results for all libraries")

# validator
class RedundancyAnalysisResult(BaseModel):
    """冗余分析结果"""
    library_name: str = Field(description="Library name exactly as provided")
    should_keep: bool = Field(description="Whether this library should be kept")
    reasoning: str = Field(description="Professional analysis explaining why keep or remove")

# validator
class RedundancyAnalysisResults(BaseModel):
    """第二步冗余分析结果"""
    results: List[RedundancyAnalysisResult] = Field(
        description="Redundancy analysis results for all reasonable libraries")
