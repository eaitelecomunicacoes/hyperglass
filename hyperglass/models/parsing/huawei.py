"""Data Models for Parsing Huawei Response."""

# Standard Library
from typing import List

# Third Party
from pydantic import StrictInt, StrictStr, StrictBool

# Project
from hyperglass.log import log

# Local
from ..main import HyperglassModel
from .serialized import ParsedRoutes

RPKI_STATE_MAP = {
    "invalid": 0,
    "valid": 1,
    "unknown": 2,
    "unverified": 3,
}


class _HuaweiBase(HyperglassModel):
    class Config:
        extra = "ignore"


class HuaweiPaths(_HuaweiBase):
    available: int
    best: int
    select: int
    best_external: int
    add_path: int


class HuaweiRouteTableEntry(_HuaweiBase):
    prefix: StrictStr  # BGP routing table entry information of
    from_addr: StrictStr
    duration: StrictInt
    direct_out_interface: StrictStr
    original_next_hop: StrictStr
    relay_ip_next_hop: StrictStr
    relay_ip_out_interface: StrictStr
    qos: StrictStr
    communities: List[StrictStr] = []
    large_communities: List[StrictStr] = []
    ext_communities: List[StrictStr] = []
    as_path: List[StrictInt] = []
    origin: StrictStr
    metric: StrictInt = 0  # MED
    local_preference: StrictInt
    preference_value: StrictInt
    is_valid: StrictBool
    is_external: StrictBool
    is_backup: StrictBool
    is_best: StrictBool
    is_selected: StrictBool
    preference: StrictInt


class HuaweiRoute(_HuaweiBase):
    """Validation model for route-table data."""

    local_router_id: StrictStr
    local_as_number: int
    paths: HuaweiPaths
    rt_entry: List[HuaweiRouteTableEntry] = []

    def serialize(self):
        """Convert the Huawei-specific fields to standard parsed data model."""
        routes = []
        count = 0
        for route in self.rt_entry:
            count += 1
            routes.append(
                {
                    "prefix": route.prefix,
                    "active": route.is_selected,
                    "age": route.duration,
                    "weight": route.preference,
                    "med": route.metric,
                    "local_preference": route.local_preference,
                    "as_path": route.as_path,
                    "communities": route.communities,
                    "next_hop": route.original_next_hop,
                    "source_as": 0,
                    "source_rid": "",
                    "peer_rid": route.from_addr,
                    "rpki_state": RPKI_STATE_MAP.get("valid") if route.is_valid else RPKI_STATE_MAP.get("unknown"),
                }
            )

        serialized = ParsedRoutes(
            vrf="default", count=count, routes=routes, winning_weight="low",
        )

        log.debug("Serialized Huawei response: {}", serialized)
        return serialized
