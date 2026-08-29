from enum import StrEnum

class ConfidenceGrade(StrEnum):
    A="A"; B="B"; C="C"; D="D"; E="E"

class VerificationStatus(StrEnum):
    PRIMARY_VERIFIED="PRIMARY_VERIFIED"
    SECONDARY_VERIFIED="SECONDARY_VERIFIED"
    SECONDARY_UNVERIFIED="SECONDARY_UNVERIFIED"
    ESTIMATED="ESTIMATED"
    ASSUMPTION="ASSUMPTION"

class EvidenceType(StrEnum):
    FILING_FACT="filing_fact"
    MARKET_DATA="market_data"
    CONSENSUS="consensus"
    MANAGEMENT_STATEMENT="management_statement"
    INDUSTRY_DATA="industry_data"
    CALCULATED_METRIC="calculated_metric"
    STATISTICAL_RESULT="statistical_result"
    ANALYST_ASSUMPTION="analyst_assumption"
