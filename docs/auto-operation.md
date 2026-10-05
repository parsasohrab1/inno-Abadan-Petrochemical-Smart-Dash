# Smart Operator (Auto Operation) design

Source: README §6 and FR-14..17. Inspired by Honeywell Experion Cognition and ABB Ability Genix
(Borouge implementation).

## 1. The five levels (README §6-2)

| Level | Name | Component |
|---|---|---|
| 1 Monitoring | 24/7 monitoring | `data-acquisition`, `sensor-health` |
| 2 Analysis | Failure pattern detection > 95% | `signal-processing`, `ai-engine` |
| 3 Alerting | Prioritized alert | `prediction-rul`, `alerting` |
| 4 Recommendation | Proposing corrective action | `auto-operation/engine.py` (load reduction, maintenance scheduling, part order) |
| 5 Action | Automatic execution | `auto-operation/control.py` (on/off, standby switchover) |

## 2. Online optimization and on/off control (user requirement)

The system can **automatically shut down equipment (pump/compressor/fan)** and **start its standby**.

### Decision tree for each equipment

```
fault severity < 0.25  ────────────────► monitoring only
0.25 ≤ severity < 0.55 and RUL > 72h ──► Level 4: 15% load reduction + maintenance scheduling + part order
severity ≥ 0.6  or  RUL ≤ 72h ───────► Level 5:
        ├─ has a standby? ──► SPARE_CHANGEOVER: start the standby, then stop the main, move to repair
        ├─ safety-critical and RUL ≤ 24h and no standby ──► EQUIPMENT_STOP (controlled/emergency)
        └─ otherwise ──► high-priority maintenance request + 30% load reduction
```

### Instantaneous cost-benefit analysis

A changeover/stop action is proposed only when:

```
estimated savings = avoided downtime cost + avoided catastrophic failure cost
                  (from services/common/economics.py with the price list config/economics.yaml)
```

The `estimated_savings_usd` value of each action is fed to the `economics` service and appears in the
"instantaneous savings" rate of the management dashboard.

## 3. Equipment state machine (`control.py`)

```
RUNNING ──stop──► STOPPING ──► STOPPED ──start──► STARTING ──► RUNNING
   │                                    │
   └──trip──► TRIPPED                    └──► STANDBY (standby ready)  /  MAINTENANCE
```

Each transition is recorded in the `equipmentstatechange` table with `triggered_by` (auto-operation / operator:<name> /
protection). In a real environment `_send_command` connects to an OPC-UA writeback on the DCS/SIS.

## 4. Human-in-the-loop (FR-17)

| Mode (`AUTO_OP_MODE`) | Behavior |
|---|---|
| `advisory` | All actions are only "suggestions" — no automatic execution |
| `supervised` | On/off/changeover actions require operator approval; the rest are automatic |
| `autonomous` | Automatic execution except for safety-critical equipment (always human approval) |

`AUTO_OP_REQUIRE_HUMAN_APPROVAL=true` (default) makes human approval globally mandatory for
control actions. The cap `AUTO_OP_MAX_AUTONOMOUS_ACTIONS_PER_HOUR` prevents an action
storm.

## 5. API

| Method | Path | Required role |
|---|---|---|
| GET | `/actions`, `/actions/pending`, `/actions/{id}` | viewer |
| POST | `/actions/{id}/approve` \| `/reject` | operator |
| POST | `/control/{tag}/start` \| `/stop` \| `/changeover` | operator |
| GET | `/equipment/{tag}/state` | viewer |
| GET/PATCH | `/policy` | engineer (for PATCH) |
