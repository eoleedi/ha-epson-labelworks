# Epson LabelWorks ESCPL2 Protocol Research

This document describes the ESCPL2 command stream used by Epson LabelWorks printers and records the protocol assumptions made by this integration. It is an implementation-oriented research document, not an official Epson specification.

The research correlates this project's encoder with analysis of Epson's Android iLabel application by Tyalie [1], analysis and LW-700 hardware testing by igrbtn [2], and the LW-600P implementation in nospero [3].

## Contents

1. [Scope And Safety](#1-scope-and-safety)
2. [Common Protocol](#2-common-protocol)
3. [Command Set](#3-command-set)
4. [Printer Profiles](#4-printer-profiles)
5. [SDK Capability Matrix](#5-sdk-capability-matrix)
6. [Status And Media Values](#6-status-and-media-values)
7. [Implementation Boundaries](#7-implementation-boundaries)
8. [Open Questions](#8-open-questions)
9. [References](#9-references)

## 1. Scope And Safety

### 1.1 AI Disclosure

This document was generated with assistance from an AI system. The AI analyzed and synthesized the cited research and source code, but it did not operate or test a physical printer. Protocol details may contain errors and should be checked against the cited sources, captured traffic, and hardware testing before being relied upon.

### 1.2 Conventions

- Numeric values are hexadecimal unless stated otherwise.
- Multi-byte integers are little-endian unless stated otherwise.
- `ESC` means byte `1B`.
- `FF` in prose means byte `FF`; form feed is written as `0C`.
- A set raster bit prints a black dot.

### 1.3 Evidence Levels

| Term            | Meaning                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------ |
| Defined         | Byte structure agrees across all applicable implementations                                |
| Corroborated    | At least two implementations agree, without isolated hardware proof of universal semantics |
| Hardware-tested | The cited project reports successful use on the named printer                              |
| SDK-derived     | Reconstructed from Epson application or driver behavior                                    |
| Provisional     | Implemented by this project but awaiting an LW-600P capture or controlled test             |

## 2. Common Protocol

ESCPL2 jobs have four logical stages:

1. A transport carries bytes over USB, Bluetooth, or Ethernet.
2. Framed control commands configure the document and page.
3. Raster records transfer the monochrome bitmap.
4. Form-feed and document-state commands commit the page and job.

Control and raster framing are shared across the researched implementations. The LW-600P and LW-700 also share a USB transport layout and control-request set. Status response values, cutter parameters, additional page commands, and some command meanings remain model-specific.

### 2.1 Shared USB Printer Transport

The LW-600P and LW-700 share this USB layout:

| Property          | Shared value                  |
| ----------------- | ----------------------------- |
| Vendor/product ID | `04B8:0705`                 |
| Interface         | Printer class, interface`0` |
| Bulk IN endpoint  | `81`                        |
| Bulk OUT endpoint | `02`                        |
| Command language  | `ESCPL2`                    |

Printing uses bulk OUT; status data may use bulk IN or USB control transfers. The shared VID/PID cannot identify the model. Read the USB product string or IEEE-1284 `MDL` field instead.

### 2.2 Control Frame

```text
1B 7B <length> <command> <parameters...> <checksum> 7D
```

| Field          | Definition                                             |
| -------------- | ------------------------------------------------------ |
| `1B 7B`      | ASCII`ESC {`                                         |
| `length`     | Number of bytes from`command` through closing `7D` |
| `command`    | One-byte command identifier                            |
| `parameters` | Zero or more command-specific bytes                    |
| `checksum`   | `(command + sum(parameters)) & FF`                   |
| `7D`         | ASCII`}`                                             |

For `P` parameter bytes:

```text
length = P + 3
total frame size = P + 6
```

Example, density command `D` with encoded value `05`:

```text
1B 7B 04 44 05 49 7D
```

This framing is defined consistently by all three implementations [1][2][3].

### 2.3 Raster Record

One raster record represents one print-head strip across the tape:

```text
1B 2E 00 00 00 01 <dots-u16-le> <bitmap...>
```

```text
bitmap length = (dots + 7) // 8
```

Bits are packed most-significant bit first. The host emits one record for each feed position along the label [1][2][3].

This integration represents image width as label length and image height as tape width. It converts each image column into one raster record and reverses the vertical pixel order while packing. An encoder that processes image rows can produce the same orientation by rotating the image 90 degrees.

The `dots` value must not exceed the printer's printable head width. Both profiles documented here use 180 DPI. LW-700 testing measured 72 printable dots on 12 mm tape; values used by that project for other tape widths are estimates [2]. Other LabelWorks models are reported at 300 or 360 DPI [1].

### 2.4 Shared Job Spine

Both printer profiles use this core command order:

```text
Document setup: { C D G
Page setup:     L T
Raster:         ESC . records
End page:       0C
End document:   @
```

Byte `0C` is form feed and terminates a page. Framed command `@` is a print-end or document-state command. Profiles may add status commands, a leading `@`, or capability commands around this spine. They also define the values and semantics of `C`, `D`, `L`, and `T`.

### 2.5 USB Control Status Requests

Both USB profiles implement the same three IN requests:

| `bmRequestType` | `bRequest` | Setup parameters                                 | Purpose                           |
| ----------------: | -----------: | ------------------------------------------------ | --------------------------------- |
|            `C1` |       `01` | `wValue=0000`, `wIndex=0000`, `wLength=64` | Vendor GetLWStatus                |
|            `A1` |       `01` | `wValue=0000`, `wIndex=0000`, `wLength=1`  | Printer-class port status         |
|            `A1` |       `00` | `wValue=0000`, interface `wIndex=0000`       | Printer-class IEEE-1284 device ID |

Observed GetLWStatus data begins with `08`; byte 1 represents printer activity in LW-700 testing, and byte 3 carries a tape code on both models. Response length and observed values are recorded in each profile.

## 3. Command Set

### 3.1 Command Summary

| Command        |      Parameters | Purpose                                 | Evidence                                              |
| -------------- | --------------: | --------------------------------------- | ----------------------------------------------------- |
| `!` (`21`) |            none | Reset printer                           | SDK-derived [1]                                       |
| `+` (`2B`) |        one byte | Feed, optionally cut                    | SDK-derived [1]                                       |
| `@` (`40`) |            none | Print-end/document-state                | Corroborated; placement varies [1][2][3]              |
| `C` (`43`) |      four bytes | Cutter configuration                    | Corroborated; values vary [1][2][3]                   |
| `D` (`44`) |        one byte | Print density                           | Corroborated [1][2][3]                                |
| `G` (`47`) |            none | Unknown job option                      | Corroborated [1][2][3]                                |
| `H` (`48`) |        one byte | Unknown capability option               | SDK-derived [1]                                       |
| `I` (`49`) |       two bytes | Status request, protocol v2             | SDK-derived [1]                                       |
| `L` (`4C`) |          u32 LE | Page length in feed positions           | Corroborated [1][2][3]                                |
| `O` (`4F`) |       two bytes | Tape-width-related page option          | SDK-derived; used by LW-700 [1][2]                    |
| `Q` (`51`) |       two bytes | Status request, protocol v1             | Corroborated [1][3]                                   |
| `T` (`54`) |          u16 LE | Width or margin, depending on profile   | Defined framing; profile-specific semantics [1][2][3] |
| `W` (`57`) |          u16 LE | Capability-level-2 width option         | SDK-derived; used by LW-700 [1][2]                    |
| `X` (`58`) |        one byte | Continuous half-cut option              | SDK-derived [1]                                       |
| `o` (`6F`) |        one byte | Object type                             | SDK-derived [1]                                       |
| `s` (`73`) |        one byte | Print speed                             | Corroborated [1][2]                                   |
| `t` (`74`) |     three bytes | Tape width, kind, and ribbon properties | Corroborated [1][2]                                   |
| `y` (`79`) |            none | Print-priority option                   | SDK-derived [1]                                       |
| `{` (`7B`) | `00 00 53 54` | Job initialization signature            | Corroborated [1][2][3]                                |

Some names remain descriptive rather than definitive because their effects were inferred from decompiled option names or command placement.

### 3.2 Fixed Frames

| Operation                 | Bytes                             |
| ------------------------- | --------------------------------- |
| Reset printer             | `1B 7B 03 21 21 7D`             |
| Feed without cut          | `1B 7B 04 2B 00 2B 7D`          |
| Feed with cut             | `1B 7B 04 2B 01 2C 7D`          |
| Print-end/document-state  | `1B 7B 03 40 40 7D`             |
| Unknown job option`G`   | `1B 7B 03 47 47 7D`             |
| Enable protocol-v1 status | `1B 7B 05 51 05 00 56 7D`       |
| Reset protocol-v1 status  | `1B 7B 05 51 00 00 51 7D`       |
| Job initialization        | `1B 7B 07 7B 00 00 53 54 22 7D` |

### 3.3 Page Geometry

Command `L` carries the page length as a 32-bit little-endian count of feed positions. It includes all content records and leading or trailing blank records.

```text
1B 7B 07 4C <length-u32-le> <checksum> 7D
```

Command `T` carries a 16-bit little-endian profile-specific value:

```text
1B 7B 05 54 <value-u16-le> <checksum> 7D
```

- The LW-600P implementations set `T` to the configured margin [1][3].
- The working LW-700 stream sets `T` to the across-tape raster dot count [2].

The strongest current definition is profile-specific. Width and margin must not be assumed interchangeable on another model.

### 3.4 Print Density

Command `D` encodes density as:

```text
encoded density = requested density + 5
```

The SDK-derived range is decimal `-5` through `5`, while the observed Android UI exposed decimal `-3` through `3` [1]. This integration accepts the full SDK-derived range. The LW-700 implementation defaults to requested density `4` to avoid cold-head gaps [2].

### 3.5 Cutter Configuration

Command `C` carries four bytes:

| Behavior            | `01` variant  | `02` variant  |
| ------------------- | --------------- | --------------- |
| No cut              | `00 00 00 00` | `00 00 00 00` |
| Cut each page/label | `01 01 01 01` | `02 02 01 01` |
| Cut after job       | `01 00 01 01` | `02 00 01 01` |

The Android-derived research tentatively associates `01` and `02` with fast and slow half-cut modes [1]. The LW-600P implementations use the `01` variants [3]. The LW-700 encoder uses `02`, but only `02 00 01 01` with one end cut is reported as reliable on hardware. The each-page `02 02 01 01` value is reverse-engineered and should not be considered equally safe [2].

Cut behavior must be selected by model. Extra or mid-job cuts can power off the tested LW-700 [2].

## 4. Printer Profiles

### 4.1 LW-600P, Provisional Capability Level 1

#### Evidence

- Epson's Android SDK table assigns the LW-600P capability level 1 and 180 DPI [1].
- Nospero implements the same level-1 command set for the LW-600P over Bluetooth [3].
- The Android research was hardware-verified only on an LW-C410 [1].
- Nospero does not publish a packet capture or explicit hardware-validation record [3].
- This project has directly verified LW-600P USB descriptors and read-only status requests, but has not sent or validated a print stream.

The profile is therefore corroborated implementation evidence, not completed hardware proof.

#### Transport

Nospero uses Bluetooth RFCOMM channel 1 at 115200 8N1 [3]. This integration supports Bluetooth serial and generic USB bulk transports.

Read-only USB inspection on project hardware confirmed:

| Property           | LW-600P value                                                           |
| ------------------ | ----------------------------------------------------------------------- |
| USB version        | 1.10, full speed                                                        |
| Device release     | `0100`                                                                |
| Manufacturer       | `EPSON`                                                               |
| Product            | `EPSON LW-600P`                                                       |
| Configuration      | One, self-powered, 100 mA                                               |
| Interface details  | Subclass`01`, bidirectional protocol `02`, 64-byte endpoint packets |
| IEEE-1284 identity | `MFG:EPSON;CMD:ESCPL2;MDL:LW-600P;CLS:PRINTER;`                       |

The shared transport parameters are defined in section 2.1.

#### Settings

| Setting                  | LW-600P value                                          |
| ------------------------ | ------------------------------------------------------ |
| Cutter                   | `01` variants                                        |
| `L`                    | Content width plus leading and trailing margin records |
| `T`                    | Margin in dots                                         |
| Additional page commands | None for capability level 1                            |
| Status                   | Protocol-v1 textual status via`Q`                    |

#### Print Sequence

The Android SDK-derived sequence is [1]:

```text
Q reset
Q reset
!
Q enable
@ { C D G
Q enable
L T
raster records
0C
wait for ST=05
Q reset
Q reset
```

This integration currently sends:

```text
Read-only status preflight and installed tape-width validation
!
Q enable
@ { C D G
Q enable
L T
raster records
0C
@
Bluetooth: poll with Q enable until ST=05
USB: poll GetLWStatus C1/01 until activity byte 1 is 00
Q reset
```

The differences in reset count, polling, and final status behavior are implementation choices awaiting LW-600P validation. USB configuration accepts only devices whose product string identifies an LW-600P; the shared VID/PID alone is insufficient.

The preflight rejects the job before reset, raster, or cutter commands if the printer is busy, reports an error, has an unknown tape code, or contains tape whose detected width differs from the requested label width.

Nospero also emits both leading and trailing `@` frames, although its tests expect only the final occurrence. It therefore corroborates the current stream structure but does not resolve whether the leading `@` is required [3].

#### Status

##### Bluetooth Protocol V1

The LW-600P capability profile uses the shared 64-byte textual status format defined in section 6.1. Nospero and this integration require byte 63 to be `FF`, an implementation assumption not specified by the Android research [1][3].

##### USB Control Status

The following USB IN requests were observed directly on an idle LW-600P. No bulk OUT data or ESCPL2 command was sent.

| Request              | Observed LW-600P response                                  |
| -------------------- | ---------------------------------------------------------- |
| GetLWStatus`C1/01` | 64 bytes:`08 00 00 03` followed by 60 zero bytes         |
| Port status`A1/01` | `18`                                                     |
| Device ID`A1/00`   | `00 2F` followed by the 45-byte IEEE-1284 identity above |

Response byte 3 from GetLWStatus was `03`, consistent with the documented raw 12 mm tape code. The physical cartridge width was not independently checked during this read-only probe. The first response byte, `08`, may describe the meaningful status length even though the device returned the full requested 64 bytes; this interpretation remains unverified.

A 750 ms read from bulk IN endpoint `81`, without first sending a status command, timed out. This establishes only that no unsolicited data arrived during that interval; it does not prove that USB textual status is unsupported.

The integration uses GetLWStatus for USB status and completion polling. It does not parse the binary USB response as a textual protocol-v1 frame.

### 4.2 LW-700 USB, Hardware-Tested

#### Evidence

- LW700Print reconstructed the command stream from Epson's macOS filter and option handling [2].
- Its author reports successful printing and status queries on an LW-700 connected over USB [2].
- This project has not independently tested an LW-700.
- Encoder defaults that were not tested in isolation remain implementation evidence rather than universal command semantics.

#### Transport

| Property           | LW-700 value                                     |
| ------------------ | ------------------------------------------------ |
| Product model      | `LW-700`                                       |
| IEEE-1284 identity | `MFG:EPSON;CMD:ESCPL2;MDL:LW-700;CLS:PRINTER;` |

The shared transport parameters are defined in section 2.1. Vendor engage requests `02`, `03`, and `04` stall and are not required on the tested printer [2].

#### Settings

| Setting      | LW-700 value                 |
| ------------ | ---------------------------- |
| Reliable cut | `02 00 01 01`, one end cut |
| `L`        | Total feed-position count    |
| `T`        | Across-tape raster dot count |
| `O`        | `00 00` default            |
| `W`        | `00 00` default            |
| `t`        | `00 00 00` default         |
| `s`        | `00` default               |

The zero-valued page options are encoder defaults reconstructed from the macOS driver, not independently proven tape-property semantics [2].

#### Print Sequence

Relative to the shared job spine, the LW-700 adds `s` after `G` and adds `O W t` after `T`:

```text
Document setup: { C D G s
Page setup:     L T O W t
```

The default encoder emits 64 leading and 64 trailing blank raster records, approximately 9 mm on each side at 180 DPI. These records compensate for the physical separation between print head and cutter and are distinct from command `T` [2].

#### Status

##### USB Control Status

| Request              | Observed LW-700 response                            |
| -------------------- | --------------------------------------------------- |
| GetLWStatus`C1/01` | Eight bytes, for example`08 00 00 04 00 00 00 00` |
| Port status`A1/01` | `38`                                              |
| Device ID`A1/00`   | IEEE-1284 identity above                            |

In GetLWStatus:

- Byte 1 was observed as `02` or `05` while busy and returns to `00` when idle.
- Byte 3 carries the tape code.
- Tape code `03` was confirmed as 12 mm.
- Tape code `04` was confirmed as 18 mm.
- Codes `01` = 6 mm, `02` = 9 mm, and `05` = 24 mm are sequential assumptions, not hardware-confirmed mappings.

The current LW-700 status helper reads byte 3 but does not use byte 1 to wait for print completion [2]. This binary response must not be parsed as the LW-600P textual status frame.

## 5. SDK Capability Matrix

The Android-derived page environment always contains `L` and `T`, then adds commands by product capability [1]:

| Capability | Additional page commands                        |
| ---------: | ----------------------------------------------- |
|          1 | None                                            |
|          2 | `O`, `W`, `t`                             |
|          3 | `H`, `s`                                    |
|          4 | `H`, `s`, `X`, optionally `o` and `y` |
|          5 | Optionally`y`                                 |

These levels describe product features, not evidence quality. Most model assignments in [1] are SDK-derived rather than hardware-tested.

## 6. Status And Media Values

### 6.1 Textual Protocol V1 Status

The Android-derived protocol-v1 response is a 64-byte textual frame beginning with `@` [1]:

```text
@ST:00;ER:00;TW:03;...
```

| Field          | Meaning             |
| -------------- | ------------------- |
| `ST`         | Printer state       |
| `ER`         | Error code          |
| `TW`         | Raw tape-width code |
| `TR`         | Tape kind           |
| `EI`, `EJ` | Error details       |
| `TO`         | Tape option         |
| `IR`         | Ink ribbon          |
| `RR`         | Remaining ribbon    |

The Android research does not define a required final byte. Nospero and this integration require byte 63 to be `FF` [3]. Their parsers accept either `:` or `=` between keys and values because they locate the key and read the value at a fixed offset.

### 6.2 Printer States

Common textual `ST` values from the Android research include [1]:

|  Value | State                    |
| -----: | ------------------------ |
| `00` | Idle                     |
| `01` | Feeding                  |
| `02` | Printing                 |
| `03` | Data sending             |
| `04` | Feed end                 |
| `05` | Print end                |
| `06` | Pick-and-print printing  |
| `10` | Demo printing            |
| `11` | Device feeding           |
| `12` | Device printing          |
| `13` | Firmware updating        |
| `20` | Small-roll waiting       |
| `22` | Waiting for tape removal |
| `FF` | Unexpected error         |

Additional engraving states are documented in [1]. Their applicability depends on the printer.

### 6.3 Normalized Tape-Width Enum

The Android SDK defines this normalized enum [1]:

|   Code |  Tape width |
| -----: | ----------: |
| `01` |        4 mm |
| `02` |        6 mm |
| `03` |        9 mm |
| `04` |       12 mm |
| `05` |       18 mm |
| `06` |       24 mm |
| `07` |       36 mm |
| `08` | 24 mm cable |
| `09` | 36 mm cable |
| `0A` |       50 mm |
| `0B` |      100 mm |
| `0C` | Newer 50 mm |

### 6.4 Raw Textual `TW` Codes

The textual Bluetooth `TW` field contains a raw cartridge code, not the normalized enum. The mapping is defined in [1] and implemented in full by nospero [3]. This integration currently implements common values `01` through `06` and `51` through `56`.

|      Raw`TW` |  Tape width |
| -------------: | ----------: |
| `0B`, `5B` |        4 mm |
| `01`, `51` |        6 mm |
| `02`, `52` |        9 mm |
| `03`, `53` |       12 mm |
| `04`, `54` |       18 mm |
| `05`, `55` |       24 mm |
| `06`, `56` |       36 mm |
|         `11` | 24 mm cable |
|         `12` | 36 mm cable |
|         `21` |       50 mm |
|         `23` |      100 mm |
| `07`, `57` | Newer 50 mm |

Confirmed LW-700 USB codes `03` and `04` align with this common raw sequence, but they are carried in binary response byte 3 rather than a textual `TW` field [2]. Code interpretation must remain part of the response and model profile.

## 7. Implementation Boundaries

Only control framing and raster encoding should be shared unconditionally across models. A model and transport profile must define:

- DPI and printable head width
- transport setup and model identification
- document and page command sequence
- meaning of command `T`
- cutter parameters
- leading and trailing feed requirements
- status request and response format
- tape-code mapping

The current integration implements the provisional LW-600P profile. It must not be reused unchanged for the LW-700.

## 8. Open Questions

- What complete USB and Bluetooth exchanges does an LW-600P produce?
- Is the leading `@` required by an LW-600P, tolerated, or incorrect?
- Does an LW-600P status frame always end in `FF`, and which field separator does its firmware emit?
- Does `T` have model-dependent behavior, or is one existing description mislabeled?
- What are the exact effects of `G`, `H`, and `O`?
- Which additional USB IDs are shared across LabelWorks models or regional variants?
- Which cutter variants are safe for each mechanism?
- Do firmware revisions alter capability commands or status fields?

## 9. References

1. Tyalie, *Reverse Engineering: Epson Label printer protocol*, Android iLabel SDK analysis with LW-C410 Bluetooth-v1 hardware verification: [https://github.com/tyalie/RE-epson-label-printer/blob/main/protocol.md](https://github.com/tyalie/RE-epson-label-printer/blob/main/protocol.md)
2. igrbtn, *Epson LabelWorks LW-700 USB protocol notes*, macOS filter analysis and LW-700 USB hardware validation: [https://github.com/igrbtn/LW700Print/blob/main/docs/PROTOCOL.md](https://github.com/igrbtn/LW700Print/blob/main/docs/PROTOCOL.md)
3. oxplot, *nospero*, an LW-600P Bluetooth implementation with command and parser tests: [https://github.com/oxplot/nospero](https://github.com/oxplot/nospero)

License notices for source material incorporated by this project are preserved in [THIRD_PARTY_LICENSES.md](../THIRD_PARTY_LICENSES.md).
