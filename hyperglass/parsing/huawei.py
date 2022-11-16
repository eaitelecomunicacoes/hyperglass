"""Parse Huawei Response to Structured Data."""

# Standard Library
from typing import Dict, List, Sequence

# Third Party
from pydantic import ValidationError

# Project
from hyperglass.log import log
from hyperglass.exceptions import ParsingError
from hyperglass.models.parsing.huawei import HuaweiRoute


def remove_prefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def _extract_paths(line: str) -> Dict:
    """Ex.: " Paths:   3 available, 1 best, 1 select, 0 best-external, 0 add-path" """

    values = remove_prefix(line, " Paths:   ").split(',')
    available = 0
    best = 0
    select = 0
    best_external = 0
    add_path = 0

    for value in values:
        v, name = value.strip().split(" ")
        if name == "available":
            available = int(v)
        elif name == "best":
            best = int(v)
        elif name == "select":
            select = int(v)
        elif name == "best-external":
            best_external = int(v)
        elif name == "add-path":
            add_path = int(v)

    return {
        "available": available,
        "best": best,
        "select": select,
        "best_external": best_external,
        "add_path": add_path,
    }


def _extract_route_entries(lines: List[str]) -> List[Dict]:
    """ Ex.:
     BGP routing table entry information of 8.8.8.0/24:
     From: 0.0.0.0 (0.0.0.0)
     Route Duration: 84d11h53m07s
     Direct Out-interface: Eth-Trunk1.2605
     Original nexthop: 0.0.0.0
     Qos information : 0x0
     Community: <28145:24>
     AS-path 15169, origin igp, MED 0, localpref 150, pref-val 0, valid, external, best, select, pre 255
     Advertised to such 1 peers:
        0.0.0.0
    """
    routes = []

    size = lines.__len__()
    idx_list = [idx + 1 for idx, val in enumerate(lines) if val == ""]
    entries = [lines[i: j] for i, j in zip([0] + idx_list, idx_list + ([size] if idx_list[-1] != size else []))] if idx_list else [lines]

    for route_entry in entries:
        prefix = ""  # BGP routing table entry information of
        from_addr = ""  # From:
        duration = 0  # Route Duration:
        direct_out_interface = ""
        original_next_hop = ""
        relay_ip_next_hop = ""
        relay_ip_out_interface = ""
        qos = ""
        communities = []
        large_communities = []
        ext_communities = []
        as_path = []
        origin = ""
        metric = 0  # MED
        local_preference = 0
        preference_value = 0
        is_valid = False
        is_external = False
        is_backup = False
        is_best = False
        is_selected = False
        preference = 0

        for info in route_entry:
            info = info.strip()
            if info.startswith("BGP routing table entry information of"):
                prefix = remove_prefix(info, "BGP routing table entry information of ")[:-1]
            elif info.startswith("From:"):
                from_addr = remove_prefix(info, "From: ").split(" (")[0]
            elif info.startswith("Route Duration:"):
                d = remove_prefix(info, "Route Duration: ").replace("d", " ").replace("h", " ").replace("m", " ",).replace("s", "").split(" ")
                duration = int(d[0]) * 24 * 60 * 60 + int(d[1]) * 60 * 60 + int(d[2]) + 60 + int(d[3])
            elif info.startswith("Direct Out-interface:"):
                direct_out_interface = remove_prefix(info, "Direct Out-interface: ")
            elif info.startswith("Original nexthop:"):
                original_next_hop = remove_prefix(info, "Original nexthop: ")
            elif info.startswith("Relay IP Nexthop:"):
                relay_ip_next_hop = remove_prefix(info, "Relay IP Nexthop: ")
            elif info.startswith("Relay IP Out-Interface:"):
                relay_ip_out_interface = remove_prefix(info, "Relay IP Out-Interface: ")
            elif info.startswith("Qos information :"):
                qos = remove_prefix(info, "Qos information : ")
            elif info.startswith("Community:"):
                communities = remove_prefix(info, "Community: ").split(", ")
            elif info.startswith("Large-Community:"):
                large_communities = remove_prefix(info, "Large-Community: ").split(", ")
            elif info.startswith("Ext-Community:"):
                ext_communities = remove_prefix(info, "Ext-Community: ").split(", ")
            elif info.startswith("AS-path"):
                values = info.split(",")
                for v in values:
                    v = v.strip()
                    if v.startswith("AS-path"):
                        as_path = [int(a) for a in remove_prefix(v, "AS-path ").split(" ")]
                    elif v.startswith("origin"):
                        origin = remove_prefix(v, "origin ")
                    elif v.startswith("MED"):
                        metric = int(remove_prefix(v, "MED "))
                    elif v.startswith("localpref"):
                        local_preference = int(remove_prefix(v, "localpref "))
                    elif v.startswith("pref-val"):
                        preference_value = int(remove_prefix(v, "pref-val "))
                    elif v.startswith("valid"):
                        is_valid = True
                    elif v.startswith("external"):
                        is_external = True
                    elif v.startswith("backup"):
                        is_backup = True
                    elif v.startswith("best"):
                        is_best = True
                    elif v.startswith("select"):
                        is_selected = True
                    elif v.startswith("pre"):
                        preference = int(remove_prefix(v, "pre "))

            #  Advertised to such 1 peers:
            #     0.0.0.0

        routes.append(
            {
                "prefix": prefix,
                "from_addr": from_addr,
                "duration": duration,
                "direct_out_interface": direct_out_interface,
                "original_next_hop": original_next_hop,
                "relay_ip_next_hop": relay_ip_next_hop,
                "relay_ip_out_interface": relay_ip_out_interface,
                "qos": qos,
                "communities": communities,
                "large_communities": large_communities,
                "ext_communities": ext_communities,
                "as_path": as_path,
                "origin": origin,
                "metric": metric,
                "local_preference": local_preference,
                "preference_value": preference_value,
                "is_valid": is_valid,
                "is_external": is_external,
                "is_backup": is_backup,
                "is_best": is_best,
                "is_selected": is_selected,
                "preference": preference,
            }
        )

    return routes


def parse_huawei(output: Sequence[str]) -> Dict:  # noqa: C901
    """Parse a Huawei BGP response."""
    data = {}

    for i, response in enumerate(output):

        try:
            rows: List[str] = response.splitlines()

            if rows.__len__() < 5:
                return data

            ln = 0
            if rows[0].strip() == "":
                ln = 1

            # 00:' '
            # 01:' BGP local router ID : x.x.x.x'
            # 02:' Local AS number : xxxxx'
            # 03:' Paths:   3 available, 1 best, 1 select, 0 best-external, 0 add-path'

            parsed = {
                "local_router_id": rows[ln].split(":")[1].strip(),
                "local_as_number": int(rows[ln + 1].split(":")[1].strip()),
                "paths": _extract_paths(rows[ln + 2]),
                "rt_entry": _extract_route_entries(rows[ln + 3:]),
            }

            validated = HuaweiRoute(**parsed)
            serialized = validated.serialize().export_dict()

            if i == 0:
                data.update(serialized)
            else:
                data["routes"].extend(serialized["routes"])
        except ValidationError as err:
            log.critical(str(err))
            raise ParsingError(err.errors())

    log.debug("Serialzed: {}", data)
    return data
