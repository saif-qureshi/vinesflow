from datetime import datetime

from pydantic import BaseModel, Field, field_validator

FBR_SANDBOX_SCENARIOS = {
    "SN001": "Goods at standard rate (Registered Buyer)",
    "SN002": "Goods at standard rate (Unregistered Buyer)",
    "SN003": "Steel melting and re-rolling",
    "SN004": "Ship breaking",
    "SN005": "Goods at Reduced Rate",
    "SN006": "Exempt goods",
    "SN007": "Goods at zero-rate",
    "SN008": "3rd Schedule Goods",
    "SN009": "Cotton ginners",
    "SN010": "Telecommunication services",
    "SN011": "Toll Manufacturing",
    "SN012": "Petroleum Products",
    "SN013": "Electricity Supply to Retailers",
    "SN014": "Gas to CNG stations",
    "SN015": "Mobile Phones",
    "SN016": "Processing/Conversion of Goods",
    "SN017": "Goods (FED in ST Mode)",
    "SN018": "Services (FED in ST Mode)",
    "SN019": "Services (ICTO)",
    "SN020": "Electric Vehicle",
    "SN021": "Cement/Concrete Block",
    "SN022": "Potassium Chlorate",
    "SN023": "CNG Sales",
    "SN024": "Goods as per SRO.297(I)/2023",
    "SN025": "Non-Adjustable Supplies",
    "SN026": "Retailer Sale (Standard Rate)",
    "SN027": "Retailer Sale (3rd Schedule Goods)",
    "SN028": "Retailer Sale (Reduced Rate)",
}


class SuperAdminFbrSandboxTestRequest(BaseModel):
    scenario_codes: list[str] = Field(min_length=1, max_length=28)

    @field_validator("scenario_codes")
    @classmethod
    def validate_scenarios(cls, values: list[str]) -> list[str]:
        unique = list(dict.fromkeys(values))
        unknown = [code for code in unique if code not in FBR_SANDBOX_SCENARIOS]
        if unknown:
            raise ValueError(f"Unknown FBR sandbox scenario: {unknown[0]}")
        return unique


class SuperAdminFbrSandboxScenarioResult(BaseModel):
    code: str
    label: str
    status: str
    http_status_code: int | None = None
    fbr_status_code: str | None = None
    invoice_number: str | None = None
    errors: list[str]


class SuperAdminFbrSandboxTestResult(BaseModel):
    ok: bool
    total: int
    passed: int
    failed: int
    scenarios: list[SuperAdminFbrSandboxScenarioResult]
    started_at: datetime
    completed_at: datetime
