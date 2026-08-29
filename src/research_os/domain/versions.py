from pydantic import BaseModel, ConfigDict

from research_os.version import CORE_API_VERSION


class VersionBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    research_os_version: str
    dataset_version: str
    parser_version: str
    formula_version: str
    router_version: str
    kpi_pack_version: str
    driver_model_version: str
    forecast_version: str
    valuation_version: str
    report_version: str
    core_api_version: str = CORE_API_VERSION
