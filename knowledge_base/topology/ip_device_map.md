# IP → Device Mapping (SANDI-2024 testbed onto the IEEE 14-bus overlay)

Authoritative join between the network world (flow records) and the physical world
(the IEEE 14-bus grid in `ieee14_grid.md`). Canonical names: `entities.yaml`.
This mapping is a synthetic overlay: device identities are fictional and authored;
only their consistency is claimed, not field truth.

## Control-center systems (no primary equipment)

| IP | Device | Role |
|---|---|---|
| 10.0.0.2 | SCADA-1 | SCADA master — the IEC-104 *controlling station*. The only device that opens connections to the RTUs on TCP port 2404. Polls measurements, issues breaker commands. Located in ZONE-CC (Control Center). |
| 10.0.0.4 | ENG-WS-1 | Engineering workstation in ZONE-CC. Used for RTU configuration and maintenance; does not speak IEC-104 in normal operation. |

## Substation RTUs (IEC-104 controlled stations, GridCom GC-4000)

Each RTU answers SCADA-1 on TCP port 2404 and provides supervisory control of the
breakers at its substation. A breaker on a line between two RTU-monitored buses
appears under both RTUs (one breaker per line end).

| IP | Device | Zone | Bus | Controls breakers |
|---|---|---|---|---|
| 10.0.0.1 | RTU-1 | ZONE-N | 2 | BR-1-2, BR-2-3, BR-2-4, BR-2-5 |
| 10.0.0.3 | RTU-2 | ZONE-C | 4 | BR-2-4, BR-3-4, BR-4-5, BR-4-7, BR-4-9 |
| 10.0.0.5 | RTU-3 | ZONE-S | 6 | BR-5-6, BR-6-11, BR-6-12, BR-6-13 |
| 10.0.0.6 | RTU-4 | ZONE-S | 9 | BR-4-9, BR-7-9, BR-9-10, BR-9-14 |

Loss of communication with an RTU means **loss of visibility and control** of its
breakers — the grid keeps operating, but the operator can no longer see or switch
that substation remotely (see the physics reference for consequence reasoning).

## External addresses (not grid assets)

| Range / address | Meaning |
|---|---|
| 121.142.26.0/24 | Attack-simulation source network of the SANDI-2024 testbed. Any flow from this range is by construction attack traffic. |
| 134.221.96.0/24 | Attack-simulation auxiliary network. |
| 0.0.0.24, 0.0.0.32, 221.32.0.8, 225.138.0.8, 55.53.0.8, 8.0.6.4, 8.6.0.1 | Capture noise: spoofed, malformed, or multicast addresses observed during attacks. Not devices. |

Derivation note: device roles were read off the captures, not invented —
10.0.0.2 is the only port-2404 client (hence SCADA master); 10.0.0.1/.3/.5/.6
serve port 2404 (hence RTUs); 10.0.0.4 never uses 2404 (hence workstation).
