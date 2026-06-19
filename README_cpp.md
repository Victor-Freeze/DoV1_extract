# DoV1_extract (with Interactive Web Workspace)

`DoV1_extract` is an optimized Dolby Vision RPU (Reference Processing Unit) metadata extractor for AV1 video streams, featuring both a production-ready C++ command-line terminal program and an interactive React web interface.

It parses AV1 bitstreams enclosed in IVF containers, unpacks ITU-T T.35 metadata OBUs (Open Bitstream Units) from Dolby Laboratories, performs bit-level EMDF (Extensible Metadata Format) header parsing, formats output to Standard Dolby Vision standalone RPU sequences separated by Annex B 4-byte start codes and prefixed with the RPU type code (`00 00 00 01 19 ...` which is fully compliant with `dovi_tool`), and sorts them based on presentation timestamps (PTS).

---

## 🛠️ Key Design and Algorithm Fixes

Several critical algorithmic bugs were identified and successfully fixed in the C++, Web, and Python parsing modules:

1. **Start Code Emulation Prevention Byte Insertion (`0x03` injection)**:
   * *Problem*: Original logic checked indices in the *input* buffer (`data[i-2] == 0 && data[i-1] == 0`) rather than checking the *output* written stream sequence (`result`). This caused false matches and corrupted Dolby Vision binary formatting.
   * *Solution*: Adjusted parsing checks to inspect the active output vector/array (`result`) state.
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

* **Drag-and-Drop Workspace**: Fast file ingestion with a beautiful, responsive drag-over workspace.
* **Live Extraction Stats**: Track frames parsed, total Dolby Vision RPUs successfully unpacked, processing speed (frames/sec), and output payload sizes.
* **Live Interactive Terminal Console**: Detailed info, success, warning, and error logs recorded frame-by-frame with smooth auto-scroll.
* **C++ Code Audit & Fixes Panel**: An embedded split-screen code comparison view displaying corrected portions of `DoV1_extract.cpp`.
* **Optimized Local Stream Parsing**: Evaluates chunks using micro-task sleep yields to prevent the browser interface from freezing.

---

## 🚀 Getting Started

### Running the Web Interface Locally
1. Install prerequisites and package dependencies in the workspace:
   ```bash
   npm install
   ```
2. Start the Vite development script:
   ```bash
   npm run dev
   ```
3. Open your browser and navigate to `http://localhost:3000` (or your active web app container link).

#### How to Use the Web Interface:
1. Drag and drop your `.ivf` or `.av1` stream file into the upload zone or click to browse.
2. Click the **Start Extraction** button to process.
3. Inspect telemetry metrics and logs inside the **Live Parsing Console**. 
4. Once completed, click **Download RPU (.bin)** to obtain the fully compliant Dolby Vision binary payload.

---

## 💻 Compiling and Running the C++ Command-Line Tool

Ensure a compiler with standard C++17 support (GCC, Clang, or MSVC) is installed.

### Build:
```bash
g++ -std=c++17 -O3 DoV1_extract.cpp -o DoV1_extract
```

### Usage:
```bash
./DoV1_extract -i {input_av1_file.ivf} -o {output_rpu.bin} [-av1] [-v]
```

### Command Arguments:
* `-i`: Path to the input AV1 video file (requires an **IVF** container).
* `-o`: Path to the output binary file where the extracted Dolby Vision RPU payload will be saved.
* `-av1`: (Optional) Extract RPU in AV1-RPU format (default is h.265-RPU).
* `-v`: (Optional) Verbose list formatting details frame-by-frame.
* `-h`: Shows the help message.

---

## 🐍 Running the Python Tool

Requires **Python 3.8+**.

### Usage:
```bash
python Python/DoV1_extract.py -i {input_av1_file.ivf} -o {output_rpu.bin} [-av1] [-v]
```

### Command Arguments:
* `-i`: Path to the input AV1 video file (requires an **IVF** container).
* `-o`: Path to the output binary file where the extracted Dolby Vision RPU payload will be saved.
* `-av1`: (Optional) Extract RPU in AV1-RPU format (default is h.265-RPU).
* `-v`: (Optional) Verbose list formatting details frame-by-frame.
