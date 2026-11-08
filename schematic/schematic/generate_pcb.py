#!/usr/bin/env python3
"""Generate and route the two-layer SSEMAS module carrier PCB."""

from __future__ import annotations

from collections import defaultdict
from heapq import heappop, heappush
from pathlib import Path
import math

import pcbnew


ROOT = Path(__file__).resolve().parent
FP_ROOT = Path("/usr/share/kicad/footprints")
MM = pcbnew.FromMM
FP_IO = pcbnew.PCB_IO_KICAD_SEXPR()

BOARD_MIN = (20.32, 15.24)
BOARD_MAX = (142.24, 101.60)
ROUTE_MIN = (22.352, 17.272)
ROUTE_MAX = (140.208, 99.568)
GRID = 0.508
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)


NETS = [
    "GND", "+12V_IN", "+4V_GSM", "+5V_USB", "HC_TRIG",
    "HC_ECHO_RAW", "HC_ECHO_3V3", "SIM_TXD", "ESP_TXD_3V3",
    "SIM_RXD", "BUZZ_CTRL", "BUZZ_BASE", "BUZZ_SW", "GPIO2_GREEN",
    "LED_GREEN_A", "GPIO4_YELLOW", "LED_YELLOW_A", "GPIO26_RED",
    "LED_RED_A",
]


FOOTPRINTS = [
    # ref, library, footprint, value, x, y, rotation, pad-to-net mapping
    ("U1", str(ROOT / "HC-SR04.pretty"), "TH_HC-SR04V", "HC-SR04", 45.72, 22.86, 0, {"1": "+5V_USB", "2": "HC_TRIG", "3": "HC_ECHO_RAW", "4": "GND"}),
    ("J3", str(FP_ROOT / "Connector_PinHeader_2.54mm.pretty"), "PinHeader_1x11_P2.54mm_Vertical", "ESP32 DEVKIT", 76.20, 45.72, 90, {"1": "+5V_USB", "2": "GND", "3": "HC_TRIG", "4": "HC_ECHO_3V3", "5": "SIM_TXD", "6": "ESP_TXD_3V3", "7": "BUZZ_CTRL", "8": "GPIO2_GREEN", "9": "GPIO4_YELLOW", "10": "GPIO26_RED"}),
    ("J4", str(FP_ROOT / "Connector_PinHeader_2.54mm.pretty"), "PinHeader_1x05_P2.54mm_Vertical", "SIM800L", 104.14, 25.40, 90, {"1": "+4V_GSM", "2": "GND", "3": "SIM_TXD", "4": "SIM_RXD"}),
    ("J2", str(FP_ROOT / "Connector_PinHeader_2.54mm.pretty"), "PinHeader_1x04_P2.54mm_Vertical", "LM2596", 106.68, 91.44, 90, {"1": "+12V_IN", "2": "GND", "3": "GND", "4": "+4V_GSM"}),
    ("J1", str(FP_ROOT / "TerminalBlock_Phoenix.pretty"), "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal", "12V INPUT", 132.08, 91.44, 0, {"1": "+12V_IN", "2": "GND"}),
    ("R2", str(FP_ROOT / "Resistor_THT.pretty"), "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "2.2k", 55.88, 50.80, 0, {"1": "HC_ECHO_RAW", "2": "HC_ECHO_3V3"}),
    ("R3", str(FP_ROOT / "Resistor_THT.pretty"), "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "3.3k", 55.88, 63.50, 0, {"1": "HC_ECHO_3V3", "2": "GND"}),
    ("R4", str(FP_ROOT / "Resistor_THT.pretty"), "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "10k", 88.90, 50.80, 0, {"1": "ESP_TXD_3V3", "2": "SIM_RXD"}),
    ("R5", str(FP_ROOT / "Resistor_THT.pretty"), "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "20k", 88.90, 63.50, 0, {"1": "SIM_RXD", "2": "GND"}),
    ("R1", str(FP_ROOT / "Resistor_THT.pretty"), "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "1k", 99.06, 55.88, 0, {"1": "BUZZ_CTRL", "2": "BUZZ_BASE"}),
    ("R9", str(FP_ROOT / "Resistor_THT.pretty"), "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "100k", 104.14, 71.12, 0, {"1": "BUZZ_BASE", "2": "GND"}),
    ("Q1", str(FP_ROOT / "Package_TO_SOT_THT.pretty"), "TO-92_Inline", "2N2222", 116.84, 55.88, 90, {"1": "BUZZ_BASE", "2": "BUZZ_SW", "3": "GND"}),
    ("BZ1", str(FP_ROOT / "Buzzer_Beeper.pretty"), "Buzzer_12x9.5RM7.6", "5V ACTIVE", 127.00, 55.88, 0, {"1": "+5V_USB", "2": "BUZZ_SW"}),
    ("D1", str(FP_ROOT / "Diode_THT.pretty"), "D_DO-35_SOD27_P10.16mm_Horizontal", "1N4148", 121.92, 71.12, 0, {"1": "+5V_USB", "2": "BUZZ_SW"}),
    ("R6", str(FP_ROOT / "Resistor_THT.pretty"), "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "330", 30.48, 76.20, 0, {"1": "GPIO2_GREEN", "2": "LED_GREEN_A"}),
    ("D2", str(FP_ROOT / "LED_THT.pretty"), "LED_D3.0mm", "GREEN", 43.18, 76.20, 0, {"1": "GND", "2": "LED_GREEN_A"}),
    ("R7", str(FP_ROOT / "Resistor_THT.pretty"), "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "330", 30.48, 83.82, 0, {"1": "GPIO4_YELLOW", "2": "LED_YELLOW_A"}),
    ("D3", str(FP_ROOT / "LED_THT.pretty"), "LED_D3.0mm", "YELLOW", 43.18, 83.82, 0, {"1": "GND", "2": "LED_YELLOW_A"}),
    ("R8", str(FP_ROOT / "Resistor_THT.pretty"), "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "330", 30.48, 91.44, 0, {"1": "GPIO26_RED", "2": "LED_RED_A"}),
    ("D4", str(FP_ROOT / "LED_THT.pretty"), "LED_D3.0mm", "RED", 43.18, 91.44, 0, {"1": "GND", "2": "LED_RED_A"}),
    ("C1", str(FP_ROOT / "Capacitor_THT.pretty"), "CP_Radial_D10.0mm_P5.00mm", "1000uF LOW-ESR", 118.11, 40.64, 0, {"1": "+4V_GSM", "2": "GND"}),
    ("C2", str(FP_ROOT / "Capacitor_THT.pretty"), "C_Disc_D5.0mm_W2.5mm_P5.00mm", "100nF", 129.54, 30.48, 0, {"1": "+4V_GSM", "2": "GND"}),
    ("C3", str(FP_ROOT / "Capacitor_THT.pretty"), "CP_Radial_D6.3mm_P2.50mm", "100uF", 132.08, 43.18, 0, {"1": "+5V_USB", "2": "GND"}),
    ("C4", str(FP_ROOT / "Capacitor_THT.pretty"), "CP_Radial_D8.0mm_P3.50mm", "100uF 25V", 121.92, 88.90, 0, {"1": "+12V_IN", "2": "GND"}),
]


POWER_WIDTHS = {"+12V_IN": 1.2, "+4V_GSM": 1.2, "+5V_USB": 0.8}


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(MM(x), MM(y))


def mm_point(p: pcbnew.VECTOR2I) -> tuple[float, float]:
    return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)


def load_footprint(board, ref, lib, name, value, x, y, rotation, pad_nets, netinfo):
    fp = FP_IO.FootprintLoad(lib, name)
    if fp is None:
        raise RuntimeError(f"Unable to load {lib}:{name}")
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(point(x, y))
    fp.SetOrientationDegrees(rotation)
    fp.Reference().SetVisible(True)
    fp.Reference().SetTextSize(point(1.0, 1.0))
    fp.Reference().SetTextThickness(MM(0.15))
    fp.Value().SetVisible(False)
    board.Add(fp)
    for pad in fp.Pads():
        net_name = pad_nets.get(pad.GetNumber())
        if net_name:
            pad.SetNet(netinfo[net_name])
    return fp


def add_outline(board):
    x1, y1 = BOARD_MIN
    x2, y2 = BOARD_MAX
    for start, end in [((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))]:
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetStart(point(*start))
        shape.SetEnd(point(*end))
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetWidth(MM(0.05))
        board.Add(shape)


def add_text(board, text, x, y, size=1.2, layer=pcbnew.F_SilkS, justify=None):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(point(x, y))
    item.SetLayer(layer)
    item.SetTextSize(point(size, size))
    item.SetTextThickness(MM(max(0.15, size * 0.15)))
    if justify is not None:
        item.SetHorizJustify(justify)
    board.Add(item)


def add_track(board, net, a, b, layer, width):
    if a == b:
        return
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(point(*a))
    track.SetEnd(point(*b))
    track.SetLayer(layer)
    track.SetWidth(MM(width))
    track.SetNet(net)
    board.Add(track)


def add_via(board, net, xy, diameter=0.9, drill=0.4):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(point(*xy))
    via.SetWidth(MM(diameter))
    via.SetDrill(MM(drill))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(net)
    board.Add(via)


def cell_from_xy(xy):
    return (round((xy[0] - ROUTE_MIN[0]) / GRID), round((xy[1] - ROUTE_MIN[1]) / GRID))


def xy_from_cell(cell):
    return (ROUTE_MIN[0] + cell[0] * GRID, ROUTE_MIN[1] + cell[1] * GRID)


NX = round((ROUTE_MAX[0] - ROUTE_MIN[0]) / GRID) + 1
NY = round((ROUTE_MAX[1] - ROUTE_MIN[1]) / GRID) + 1


def route_pair(net_name, start_xy, goal_xy, pad_blocks, occupied, via_occupied, width):
    start = cell_from_xy(start_xy)
    goal = cell_from_xy(goal_xy)
    blocked = [set(), set()]
    clearance = 0.25 + width / 2
    for pad_net, bbox in pad_blocks:
        if pad_net == net_name:
            continue
        left, top, right, bottom = bbox
        ix1, iy1 = cell_from_xy((left - clearance, top - clearance))
        ix2, iy2 = cell_from_xy((right + clearance, bottom + clearance))
        for ix in range(max(0, min(ix1, ix2)), min(NX - 1, max(ix1, ix2)) + 1):
            for iy in range(max(0, min(iy1, iy2)), min(NY - 1, max(iy1, iy2)) + 1):
                cx, cy = xy_from_cell((ix, iy))
                if left - clearance <= cx <= right + clearance and top - clearance <= cy <= bottom + clearance:
                    blocked[0].add((ix, iy))
                    blocked[1].add((ix, iy))
    # Two grid cells also account for a previously routed 1.2 mm power track.
    halo = max(2, math.ceil((0.25 + width / 2) / GRID))
    for layer in (0, 1):
        for cell, owner in occupied[layer].items():
            if owner == net_name:
                continue
            for dx in range(-halo, halo + 1):
                for dy in range(-halo, halo + 1):
                    blocked[layer].add((cell[0] + dx, cell[1] + dy))
    for cell, owner in via_occupied.items():
        if owner != net_name:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    blocked[0].add((cell[0] + dx, cell[1] + dy))
                    blocked[1].add((cell[0] + dx, cell[1] + dy))
    for layer in (0, 1):
        blocked[layer].discard(start)
        blocked[layer].discard(goal)

    heap = []
    dist = {}
    parent = {}
    for layer in (0, 1):
        state = (start[0], start[1], layer)
        dist[state] = 0.0
        heappush(heap, (abs(start[0] - goal[0]) + abs(start[1] - goal[1]), 0.0, state))
    final = None
    while heap:
        _, cost, state = heappop(heap)
        if cost != dist.get(state):
            continue
        x, y, layer = state
        if (x, y) == goal:
            final = state
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= NX or ny < 0 or ny >= NY or (nx, ny) in blocked[layer]:
                continue
            preferred = (layer == 0 and dy == 0) or (layer == 1 and dx == 0)
            step = 1.0 if preferred else 1.35
            nstate = (nx, ny, layer)
            ncost = cost + step
            if ncost < dist.get(nstate, float("inf")):
                dist[nstate] = ncost
                parent[nstate] = state
                heuristic = abs(nx - goal[0]) + abs(ny - goal[1])
                heappush(heap, (ncost + heuristic, ncost, nstate))
        other = 1 - layer
        if (x, y) not in blocked[other]:
            nstate = (x, y, other)
            ncost = cost + 10.0
            if ncost < dist.get(nstate, float("inf")):
                dist[nstate] = ncost
                parent[nstate] = state
                heuristic = abs(x - goal[0]) + abs(y - goal[1])
                heappush(heap, (ncost + heuristic, ncost, nstate))
    if final is None:
        neighborhood = {
            layer: [
                (dx, dy, (goal[0] + dx, goal[1] + dy) in blocked[layer])
                for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))
            ]
            for layer in (0, 1)
        }
        raise RuntimeError(f"Router failed for {net_name}: {start_xy} -> {goal_xy}; goal blockers={neighborhood}")
    path = [final]
    while path[-1] not in ((start[0], start[1], 0), (start[0], start[1], 1)):
        path.append(parent[path[-1]])
    path.reverse()
    return path


def commit_path(board, net, net_name, start_xy, goal_xy, path, occupied, via_occupied, width):
    first_cell = (path[0][0], path[0][1])
    last_cell = (path[-1][0], path[-1][1])
    add_track(board, net, start_xy, xy_from_cell(first_cell), LAYERS[path[0][2]], width)

    run_start = path[0]
    previous = path[0]
    direction = None
    for current in path[1:]:
        if current[2] != previous[2]:
            add_track(board, net, xy_from_cell((run_start[0], run_start[1])), xy_from_cell((previous[0], previous[1])), LAYERS[previous[2]], width)
            add_via(board, net, xy_from_cell((current[0], current[1])))
            via_occupied[(current[0], current[1])] = net_name
            run_start = current
            direction = None
        else:
            new_direction = (current[0] - previous[0], current[1] - previous[1])
            if direction is not None and new_direction != direction:
                add_track(board, net, xy_from_cell((run_start[0], run_start[1])), xy_from_cell((previous[0], previous[1])), LAYERS[previous[2]], width)
                run_start = previous
            direction = new_direction
        previous = current
    add_track(board, net, xy_from_cell((run_start[0], run_start[1])), xy_from_cell((previous[0], previous[1])), LAYERS[previous[2]], width)
    add_track(board, net, xy_from_cell(last_cell), goal_xy, LAYERS[path[-1][2]], width)
    for x, y, layer in path:
        occupied[layer][(x, y)] = net_name


def add_ground_zone(board, net, layer):
    zone = pcbnew.ZONE(board)
    zone.SetNet(net)
    zone.SetLayer(layer)
    zone.SetLocalClearance(MM(0.3))
    zone.SetMinThickness(MM(0.25))
    zone.SetThermalReliefGap(MM(0.3))
    zone.SetThermalReliefSpokeWidth(MM(0.4))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    poly = zone.Outline()
    poly.NewOutline()
    inset = 0.5
    for x, y in [
        (BOARD_MIN[0] + inset, BOARD_MIN[1] + inset),
        (BOARD_MAX[0] - inset, BOARD_MIN[1] + inset),
        (BOARD_MAX[0] - inset, BOARD_MAX[1] - inset),
        (BOARD_MIN[0] + inset, BOARD_MAX[1] - inset),
    ]:
        poly.Append(MM(x), MM(y))
    board.Add(zone)


def main():
    board = pcbnew.BOARD()
    board.SetFileName(str(ROOT / "schematic.kicad_pcb"))
    board.GetDesignSettings().m_TrackMinWidth = MM(0.25)
    board.GetDesignSettings().m_ViasMinSize = MM(0.8)
    board.GetDesignSettings().m_MinThroughDrill = MM(0.3)

    netinfo = {}
    for name in NETS:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        netinfo[name] = net

    add_outline(board)
    fps = {}
    for entry in FOOTPRINTS:
        fp = load_footprint(board, *entry, netinfo)
        fps[entry[0]] = fp

    # Four grounded/non-plated mechanical mounting holes.
    for ref, x, y in [("H1", 25.40, 20.32), ("H2", 137.16, 20.32), ("H3", 25.40, 96.52), ("H4", 137.16, 78.74)]:
        fp = FP_IO.FootprintLoad(str(FP_ROOT / "MountingHole.pretty"), "MountingHole_3.2mm_M3")
        fp.SetReference(ref)
        fp.SetPosition(point(x, y))
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        board.Add(fp)

    add_text(board, "SSEMAS SMART SEWAGE MONITOR", 81.28, 18.3, 1.5)
    add_text(board, "REV 2.0  |  12V INPUT / 4V GSM / USB 5V", 81.28, 99.0, 0.9)
    add_text(board, "HC-SR04", 45.72, 39.0, 1.0)
    add_text(board, "ESP32 CABLE", 76.20, 40.8, 1.0)
    add_text(board, "SIM800L", 109.22, 20.0, 1.0)
    add_text(board, "LM2596: IN+ IN- OUT- OUT+", 106.68, 96.0, 0.8)
    add_text(board, "12V", 132.08, 84.0, 1.0)
    add_text(board, "G   Y   R", 43.18, 96.0, 0.9)
    add_text(board, "SET BUCK TO 4.0V BEFORE FITTING GSM", 106.68, 80.0, 0.9)

    pad_blocks = []
    net_pads = defaultdict(list)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            net_name = pad.GetNetname()
            pos = mm_point(pad.GetPosition())
            if net_name:
                net_pads[net_name].append(pos)
            bbox = pad.GetBoundingBox()
            pad_blocks.append(
                (
                    net_name or "<NO_NET>",
                    (
                        pcbnew.ToMM(bbox.GetLeft()), pcbnew.ToMM(bbox.GetTop()),
                        pcbnew.ToMM(bbox.GetRight()), pcbnew.ToMM(bbox.GetBottom()),
                    ),
                )
            )

    occupied = [dict(), dict()]
    via_occupied = {}
    priority = ["+12V_IN", "+4V_GSM", "+5V_USB", "BUZZ_SW", "BUZZ_BASE", "BUZZ_CTRL"]
    route_order = priority + [n for n in NETS if n not in {"GND", *priority}]
    for net_name in route_order:
        pads = net_pads.get(net_name, [])
        if len(pads) < 2:
            continue
        root = pads[0]
        width = POWER_WIDTHS.get(net_name, 0.4)
        for target in sorted(pads[1:], key=lambda p: abs(p[0] - root[0]) + abs(p[1] - root[1])):
            path = route_pair(net_name, root, target, pad_blocks, occupied, via_occupied, width)
            commit_path(board, netinfo[net_name], net_name, root, target, path, occupied, via_occupied, width)

    add_ground_zone(board, netinfo["GND"], pcbnew.F_Cu)
    add_ground_zone(board, netinfo["GND"], pcbnew.B_Cu)
    board.BuildConnectivity()
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(ROOT / "schematic.kicad_pcb"), board)


if __name__ == "__main__":
    main()
