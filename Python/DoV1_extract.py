import struct
import sys
import argparse

def read_leb128(data, offset):
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        value |= ((byte & 0x7F) << shift)
        if (byte & 0x80) == 0:
            break
        shift += 7
    return value, offset

class BitReader:
    def __init__(self, data):
        self.data = data
        self.bit_offset = 0
        
    def read_bits(self, n):
        value = 0
        for _ in range(n):
            if self.bit_offset >= len(self.data) * 8:
                return value
            byte = self.data[self.bit_offset // 8]
            bit = (byte >> (7 - (self.bit_offset % 8))) & 1
            value = (value << 1) | bit
            self.bit_offset += 1
        return value
        
    def read_bit(self):
        return self.read_bits(1) != 0
        
    def read_variable_bits(self, n):
        value = 0
        max_val = 1 << n
        while True:
            tmp = self.read_bits(n)
            value += tmp
            if not self.read_bit():
                break
            value <<= n
            value += max_val
        return value

    def read_remaining_bytes(self, num_bytes):
        res = []
        for _ in range(num_bytes):
            res.append(self.read_bits(8))
        return bytes(res)

def add_emulation_prevention(data):
    result = bytearray()
    for i in range(len(data)):
        if len(result) >= 2 and result[-2] == 0 and result[-1] == 0 and data[i] <= 3:
            result.append(3)
        result.append(data[i])
    return bytes(result)

def main():
    parser = argparse.ArgumentParser(description="Dolby Vision RPU extractor for AV1 (IVF) in Python")
    parser.add_argument("-i", "--input", required=True, help="Input AV1 video file (IVF container)")
    parser.add_argument("-o", "--output", required=True, help="Output RPU binary file (compatible with dovi_tool)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")
    
    args = parser.parse_args()
    
    rpu_entries = []
    frame_count = 0
    
    with open(args.input, "rb") as f:
        header = f.read(32)
        if len(header) < 32 or header[:4] != b'DKIF':
            print("Error: Not a valid IVF file (DKIF signature missing).")
            sys.exit(1)
            
        if args.verbose:
            print("Analyzing frames...")
            
        while True:
            frame_header = f.read(12)
            if len(frame_header) < 12:
                break
                
            frame_size, timestamp = struct.unpack("<IQ", frame_header)
            frame_data = f.read(frame_size)
            if len(frame_data) < frame_size:
                break
                
            offset = 0
            while offset < frame_size:
                obu_header = frame_data[offset]
                offset += 1
                
                obu_type = (obu_header >> 3) & 0x0F
                obu_extension_flag = (obu_header >> 2) & 1
                obu_has_size_field = (obu_header >> 1) & 1
                
                if obu_extension_flag:
                    offset += 1
                    
                if obu_has_size_field:
                    obu_size, offset = read_leb128(frame_data, offset)
                else:
                    obu_size = frame_size - offset
                    
                obu_end = offset + obu_size
                
                if obu_type == 5:  # Metadata OBU
                    payload_start = offset
                    metadata_type, payload_start = read_leb128(frame_data, payload_start)
                    
                    if metadata_type == 4:  # ITU-T T.35
                        country_code = frame_data[payload_start]
                        payload_start += 1
                        
                        provider_code = struct.unpack(">H", frame_data[payload_start:payload_start+2])[0]
                        payload_start += 2
                        
                        provider_oriented_code = struct.unpack(">I", frame_data[payload_start:payload_start+4])[0]
                        payload_start += 4
                        
                        if provider_code == 0x003B and provider_oriented_code == 0x00000800:
                            br = BitReader(frame_data[payload_start:obu_end])
                            
                            version = br.read_bits(2)
                            key_id = br.read_bits(3)
                            payload_id = br.read_bits(5)
                            
                            actual_payload_id = payload_id
                            if payload_id == 31:
                                actual_payload_id = br.read_variable_bits(5)
                                
                            if actual_payload_id == 225:
                                smploffste = br.read_bit()
                                duratione = br.read_bit()
                                groupide = br.read_bit()
                                codecdatae = br.read_bit()
                                discard_unknown_payload = br.read_bit()
                                
                                if smploffste: br.read_variable_bits(8)
                                if duratione: br.read_variable_bits(8)
                                if groupide: br.read_variable_bits(8)
                                if codecdatae:
                                    codec_data_len = br.read_variable_bits(8)
                                    for _ in range(codec_data_len):
                                        br.read_bits(8)
                                        
                                emdf_payload_size = br.read_variable_bits(8)
                                
                                # Do NOT align (no br.align()) because payload is offset by 4 bits
                                rpu_raw = br.read_remaining_bytes(emdf_payload_size)
                                
                                # Format RPU: starts with prefix byte 0x19
                                rpu_formatted = bytearray()
                                rpu_formatted.append(0x19)
                                rpu_formatted.extend(rpu_raw)
                                
                                rpu_entries.append((timestamp, rpu_formatted))
                                if args.verbose:
                                    print(f"Frame {frame_count:6d}: Found DoVi RPU, size {emdf_payload_size} bytes")
                                
                offset = obu_end
            frame_count += 1
            if args.verbose and frame_count % 20000 == 0:
                print(f"Processed {frame_count} frames...")
                
    if not rpu_entries:
        print("No Dolby Vision metadata found in the input file.")
        sys.exit(0)
        
    if args.verbose:
        print(f"Sorting and writing {len(rpu_entries)} RPU entries...")
        
    rpu_entries.sort(key=lambda x: x[0])
    
    with open(args.output, "wb") as out_f:
        for _, rpu_data in rpu_entries:
            rpu_with_ep = add_emulation_prevention(rpu_data)
            out_f.write(b"\x00\x00\x00\x01" + rpu_with_ep)
            
    print("Extraction complete.")
    print(f"Processed frames: {frame_count}")
    print(f"Extracted RPUs:  {len(rpu_entries)}")
    print(f"Saved to:        {args.output}")

if __name__ == "__main__":
    main()
