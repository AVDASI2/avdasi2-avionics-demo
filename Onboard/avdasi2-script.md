# RC / Telemetry Authority Script

In the wind tunnel, the Cube isn't flying anything. It's bolted into a model with no GPS, and its job is to drive the control surfaces while you take measurements. Sometimes you want those surfaces on the transmitter sticks. Sometimes you want to command them precisely from the ground station. `avdasi2.lua` lets you hand control between the two with a single switch on the transmitter.

It also gives you a second switch for SAS (stability augmentation), toggling the Cube between MANUAL and the mode set by `AVDASI2_SAS_MODE` while the transmitter has control.

This page assumes you've already read the [:material-step-forward:Lua scripting overview](lua-overview.md) and know how to get a script onto the Cube.

!!! info "Video: Setup walkthrough"
    Mapping the transmitter switches, setting `RCnn_OPTION`, uploading the script and checking the Messages tab.

## What the script does

| Switch | LOW | MID | HIGH |
|---|---|---|---|
| Authority | RC control: servos follow the transmitter | No change | Telemetry control: servos follow the ground station |
| SAS | MANUAL mode | No change | SAS mode (set by `AVDASI2_SAS_MODE`) |

The SAS switch only does anything while RC has authority.

When the authority switch goes to HIGH for the first time, the script records each managed servo's current `SERVOn_FUNCTION`, then sets it to `0` (disabled). A disabled output is ignored by the autopilot, so the ground station can command it directly, e.g. from the Servo/Relay tab in Mission Planner's Flight Data screen. When the switch goes back to LOW, the recorded functions are restored.

## Setup

**This is the step that breaks every year. Do it before anything else.**

The script doesn't know or care which channel your switch is on. It listens for a switch *function*, and you have to tell ArduPilot which channel carries that function.

1. On the transmitter, map a switch to a **spare** RC channel. Pick one that isn't used by any flight control.
2. Map a second switch to another spare channel for SAS.
3. In Mission Planner, go to **Config > Full Parameter List**.
4. Find `RCnn_OPTION` for the authority switch's channel (`nn` = channel number, e.g. `RC7_OPTION`) and set it to **`300`**.
5. Find `RCnn_OPTION` for the SAS switch's channel and set it to **`301`**.
6. Hit **Write Params**.

!!! info "If you skip this, the script will look broken. It isn't."
    With `RCnn_OPTION` missing or on the wrong channel, the script still runs, still reports `AVDASI2: started`, and then does nothing, forever, with no error message. Almost every "the script doesn't work" report we get comes down to this step.

You can check the switch is actually reaching the Cube in **Setup > Mandatory Hardware > Radio Calibration**. Flick it and watch the channel's bar: it needs to go below about 1200 at one end and above about 1800 at the other.

* [:material-information:ArduPilot - auxiliary functions (RCnn_OPTION)](https://ardupilot.org/plane/docs/common-auxiliary-functions.html)

## Upload and reboot

Upload `avdasi2.lua` to `APM/scripts/` and reboot, as described on the [:material-step-forward:Lua scripting overview](lua-overview.md).

## Verify it's working

Open the **Messages** tab in Mission Planner's Flight Data screen. After boot you should see:

```
AVDASI2: started
```

Then flick the authority switch. Each time something changes, the script sends one line:

| Message | Meaning |
|---|---|
| `AVDASI2: TELEM control` | Managed servos disabled, ground station has them |
| `AVDASI2: RC control, SAS off (MANUAL)` | Servos back on the transmitter, MANUAL mode |
| `AVDASI2: RC control, SAS on (mode N)` | Servos back on the transmitter, mode `N` from `AVDASI2_SAS_MODE` |
| `AVDASI2: SAS off (MANUAL)` / `SAS on (mode N)` | SAS switch moved while RC had authority |
| `AVDASI2: ... mode change FAILED` (warning) | ArduPilot refused the mode change |

Moving a switch to MID, or moving the SAS switch while telemetry has control, gives no message. That's intended.

You may get only `AVDASI2: started` until you move the authority switch once after boot. ArduPilot doesn't always report a switch position until it sees the switch move.

Check the rig's mounting attitude before switching SAS on. The mode set by `AVDASI2_SAS_MODE` only acts on the free axis.

## Parameters

The script creates four parameters. They appear in **Config > Full Parameter List** after the first boot with the script installed. Hit **Refresh Params** if you can't see them.

| Parameter | Default | What it does |
|---|---|---|
| `AVDASI2_RC_FUNC` | `300` | The `RCnn_OPTION` value the script treats as the authority switch. |
| `AVDASI2_SAS_FUNC` | `301` | The `RCnn_OPTION` value the script treats as the SAS switch. |
| `AVDASI2_SERVO_MASK` | `255` | Which of SERVO1–8 the script hands over. |
| `AVDASI2_SAS_MODE` | `2` | ArduPilot Plane mode number engaged when the SAS switch is HIGH. Default 2 (STABILIZE). Set to 5 for FBWA. |

You shouldn't normally need to change `AVDASI2_RC_FUNC` or `AVDASI2_SAS_FUNC`. They only need to match the `RCnn_OPTION` values you set in [Setup](#setup).

### Setting SERVO_MASK

`AVDASI2_SERVO_MASK` is a bitmask: each servo has a value, and you add up the values of the servos you want managed.

| Servo | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Value | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 |

For example, to hand over only SERVO2 and SERVO4, set `2 + 8 = 10`. All eight is `255`.

Mission Planner has no bitmask tick-box editor for script parameters, so type the number in directly. The mask is read on every handover, so a change takes effect the next time you flick the authority switch. You never need to edit the script.

!!! warning
    **Don't save parameters in Mission Planner while telemetry has authority.** The managed servos are set to `0` at that point. If those zeros get written to the Cube's storage (Write Params, loading or saving a parameter file), the script will capture `0` as the "real" function after the next reboot and can't restore it. Your surfaces won't respond to the transmitter until you re-enter the correct `SERVOn_FUNCTION` values by hand.

## Code walkthrough

!!! info "Video: Code walkthrough"
    A section-by-section look at `avdasi2.lua` and the reasoning behind each design decision.

```lua
--8<-- "code/avdasi2.lua"
```

Here we go through it in sections and focus on *why* it's written the way it is.

### Parameters

```lua
--8<-- "code/avdasi2.lua:parameters"
```

The script registers its own parameters with ArduPilot. These behave like any other parameter: visible in Mission Planner, editable over telemetry, stored on the Cube. That's what lets you configure the script from Mission Planner instead of editing and re-uploading it.

`PARAM_TABLE_KEY` (54) is an ID for this script's parameter table, and has to be unique among the scripts on the Cube.

### Cached servo functions

```lua
--8<-- "code/avdasi2.lua:saved_functions"
```

The script doesn't contain any servo functions. ArduPilot's own `SERVOn_FUNCTION` settings are the source of truth. You configure the aircraft in Mission Planner as normal, and the script copies whatever it finds.

The copy is taken on the **first** handover to telemetry, and never again. After that handover, the live value of each managed `SERVOn_FUNCTION` is `0`. Reading it again would overwrite the real function with zero.

If the authority switch is at LOW when the Cube boots, there's nothing cached yet, and the script leaves the servos alone. They already have their configured functions, so there's nothing to restore.

### Applying a handover

```lua
--8<-- "code/avdasi2.lua:apply_authority"
```

For each servo selected in `AVDASI2_SERVO_MASK`: going to RC restores the cached function, going to telemetry caches it (first time only) and sets it to `0`.

Two ArduPilot-specific points:

* `param:set()` changes the live value but **doesn't save it**. Rebooting the Cube always brings back the saved functions. That's deliberate, and it's why the [save-parameters warning](#setting-servo_mask) matters: saving is the only way the zeros can become permanent.
* ArduPilot's Lua does bitwise operations on a special `uint32_t` type. The result has to be converted with `:toint()` before comparing it to a plain number. Without it, the comparison is always false.

### Reading the switches

```lua
--8<-- "code/avdasi2.lua:reading_switches"
```

`rc:get_aux_cached()` asks ArduPilot for the last position of the switch carrying a given `RCnn_OPTION` function (`300` here). It returns `0` (LOW), `1` (MID) or `2` (HIGH), or `nil` if no channel has that option. This is why the [Setup](#setup) step is essential: the script never looks at channel numbers, so if no channel has `RCnn_OPTION = 300`, it gets `nil` forever.

`rc_state` holds the last state the script *applied*, not the last switch reading. It starts at `-1`, so the first valid reading after boot is always acted on. The script only does anything when the switch differs from that state, so parameters are only written and messages only sent on an actual change.

**MID is ignored.** A two-position switch only ever gives LOW and HIGH. A three-position switch, or a two-position switch with poorly set endpoints, can sit in the middle. Treating MID as "hold the current state" means an ambiguous switch position never flips authority by accident.

### SAS

```lua
--8<-- "code/avdasi2.lua:sas"
```

**SAS only works while RC has authority.** In telemetry mode, the managed surfaces are disabled and the ground station is commanding them directly. Stabilisation has nothing to act through, and a mode change from the transmitter would fight whatever the ground station is doing.

On every handover, `sas_state` is reset to `-1`. When control comes back to RC, the flight mode is set to match the SAS switch straight away, even if the switch hasn't moved. This covers the case where someone changed the mode from the ground station in the meantime.

LOW always selects MANUAL (Plane mode `0`). HIGH selects whichever mode number is in `AVDASI2_SAS_MODE`. The default is STABILIZE (`2`), but FBWA (`5`) is the likely choice for this rig. `math.floor()` is there because parameters are read back as floats, and `vehicle:set_mode()` needs an integer.

* [:material-information:ArduPilot - Plane flight modes](https://ardupilot.org/plane/docs/flight-modes.html)

If ArduPilot refuses the change, the script sends a warning once rather than retrying every cycle.

### Messages and scheduling

```lua
--8<-- "code/avdasi2.lua:messages_scheduling"
```

Everything that changed in one cycle goes out as a single message. Nothing is sent when nothing has changed. At 10 Hz, a message every cycle would flood the telemetry link.

ArduPilot scripts can't loop forever: each call has an instruction budget, and a script that blocks would hold up the flight code and get killed. Instead, `update()` returns itself and a delay, and ArduPilot calls it again 100 ms later.

## Troubleshooting

If you don't see `AVDASI2: started` at all, the script isn't running: go back to the [:material-step-forward:Lua scripting overview](lua-overview.md).

**I see `AVDASI2: started` and nothing else, whatever I do with the switches.**
Check the `RCnn_OPTION` step in [Setup](#setup). In order:

1. Is `RCnn_OPTION = 300` set on the channel your authority switch is actually mapped to? Check the channel number in Radio Calibration, not from memory.
2. Did you hit **Write Params** after setting it?
3. Does the switch reach below ~1200 and above ~1800 in Radio Calibration? If it only moves a little, fix the endpoints on the transmitter.
4. Have you moved the switch at least once since boot?
5. Has `AVDASI2_RC_FUNC` been changed from `300`? It must match the `RCnn_OPTION` value.

**The authority switch works but the SAS switch does nothing.**
Same step, second switch: `RCnn_OPTION = 301` on the SAS switch's channel, matching `AVDASI2_SAS_FUNC`. Also check the authority switch is at LOW, since SAS is ignored in telemetry mode, and that `AVDASI2_SAS_MODE` is set to the mode number you expect.

**Both switches do the same thing.**
Both channels have the same `RCnn_OPTION` value. One must be `300` and the other `301`.

**After a reboot, some surfaces no longer respond to the transmitter.**
Zeros were saved while telemetry had authority (see the [warning above](#setting-servo_mask)). Re-enter the correct `SERVOn_FUNCTION` values in Full Parameter List, write them, and reboot.
