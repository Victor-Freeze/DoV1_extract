# Dolby Vision RPU Extractor

An interactive, high-performance web tool and optimized C++ command-line utility for parsing Dolby Vision RPU (Reference Processing Unit) metadata from AV1 video streams. 

It processes AV1 bitstreams enclosed in IVF containers, unpacks Dolby Laboratories' ITU-T T.35 metadata Open Bitstream Units (OBUs), performs bit-level EMDF (Extensible Metadata Format) header parsing, formats the extracted RPU payloads to standard Dolby Vision standalone RPU sequences separated by Annex B 4-byte start codes and prefixed with the RPU type code (`00 00 00 01 19 ...` which is fully compliant with `dovi_tool`), and sorts them based on presentation timestamps (PTS).

---

## 🛠️ Key Design and Algorithm Fixes

During a thorough inspection and auditing of the extraction algorithm in the C++, Web, and Python implementations, several critical bugs were resolved:

1. **Start Code Emulation Prevention Byte Insertion (`0x03` injection)**:
   * *Problem*: The original loop checked indices in the *input* buffer (`data[i-2] == 0 && data[i-1] == 0`) rather than checking the *output* written stream sequence (`result`). This caused false matches and corrupted Dolby Vision binary formatting by inserting redundant alignment bytes or skipping essential ones.
   * *Solution*: Re-aligned checks to examine the active output vector/array (`result`) state directly.
2. **Byte Boundary Offset Preservation (Removing `br.align()`)**:
   * *Problem*: The EMDF header and size fields total 36 bits (4.5 bytes). As a result, the RPU payload starts at a 4-bit offset within the 5th byte. Calling `br.align()` incorrectly aligned the reader to a byte boundary before reading the payload, shifting all extracted bytes by 4 bits and causing corruption.
   * *Solution*: Removed the `br.align()` call to preserve the bit offset when copying the payload.
3. **EMDF Extension Parsing Gate and Width**:
   * *Problem*: The code was reading `payload_id_ext` as a 8-bit variable integer and adding 31 (`br.read_variable_bits(8) + 31`), which resulted in a value mismatch (`83` instead of `225`), causing the RPU block to be skipped. Furthermore, EMDF specs state it should only be parsed if `payload_id == 31`.
   * *Solution*: Configured `payload_id_ext` to be parsed as a 5-bit variable integer (`br.read_variable_bits(5)`) gated behind `if (payload_id == 31)`.
4. **Removal of HEVC NAL Header and Duplicate Trailer**:
   * *Problem*: The extraction code prepended HEVC NAL unit headers (`0x7C 0x01`) and unconditionally appended the HEVC RBSP trailing bit byte (`0x80`). However, standard `.rpu` files must not contain the HEVC stream-level NAL headers, and the raw payload already contains the `0x80` trailing byte, causing duplicates.
   * *Solution*: Removed the `0x7C 0x01` prepending and the extra `0x80` append, leaving only the standard start code `00 00 00 01` and NAL prefix `0x19` followed by the raw payload.

---

## 🖥️ Web Interface Features

* **Drag-and-Drop Workspace**: Fast file ingestion with visual file drop-zone matching standard Web usability.
* **Live Extraction Stats**: Track frames parsed, total Dolby Vision RPUs successfully unpacked, processing speed (frames/sec), and output payload sizes.
* **Live Interactive Terminal Console**: Detailed information, warning, success, and error logs recorded frame-by-frame with auto-scrolling capabilities.
* **C++ Code Audit & Fixes Panel**: An embedded split-screen code review window showcasing corrected C++ segments and architectural details.
* **Optimized Local Stream Parsing**: Evaluates file segments with micro-task sleep yields so large files do not freeze or capture the browser's thread.

---

## 🚀 Getting Started

### 1. How to run the Web Interface
Ensure you have **Node.js** installed (v18 or higher recommended).

1. In the project root, install all prerequisites and package dependencies:
   ```bash
   npm install
   ```
2. Launch the Vite development server:
   ```bash
   npm run dev
   ```
3. Open your browser and navigate to `http://localhost:3000` (or the port specified by your workspace runner).

### 2. How to use the Web Interface
1. **Load IVF stream**: Drag and drop your `.ivf` or `.av1` stream file onto the dashed upload target, or click the box to manually pick a file.
2. **Launch Parser**: Click the **Start Extraction** button that appears right below your loaded file information.
3. **Review Telemetry**: Watch the parsing progress percentage and live frame logs in the **Live Parsing Console**. 
4. **Acquire RPU**: Once parsing finishes, click **Download RPU (.bin)** to download the fully compliant Dolby Vision binary payload (suffix `_rpu.bin`), perfectly packed for standard video mastering tracks (e.g., TS Muxer, dovi_tool, or FFmpeg).

### 3. How to compile and run the CLI C++ Tool
The compiled executable requires a C++17 support environment (such as MSVC on Windows or GCC/Clang on Linux/macOS).

1. Move to the directory with source elements:
   ```bash
   cd downloaded_repo
   ```
2. Compile using GCC:
   ```bash
   g++ -std=c++17 -O3 DoV1_extract.cpp -o DoV1_extract
   ```
3. Perform translation extraction via commands:
   ```bash
   ./DoV1_extract -i input_video.ivf -o output_rpu.bin -av1 -v
   ```
   * `-i`: Path to the input AV1 `.ivf` container stream.
   * `-o`: Output path for binary Dolby Vision RPUs.
   * `-av1`: (Optional) Extract RPU in AV1-RPU format (default is h.265-RPU).
   * `-v`: (Optional) Verbose list formatting details frame-by-frame.

### 4. How to run the Python Tool
Requires **Python 3.8+**.

1. Run the extraction utility:
   ```bash
   python Python/DoV1_extract.py -i input_video.ivf -o output_rpu.bin -av1 -v
   ```
   * `-i`: Path to the input AV1 `.ivf` container stream.
   * `-o`: Output path for binary Dolby Vision RPUs.
   * `-av1`: (Optional) Extract RPU in AV1-RPU format (default is h.265-RPU).
   * `-v`: (Optional) Verbose list formatting details frame-by-frame.
