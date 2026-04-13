import serial
from datetime import datetime, timezone, timedelta

# ===== CONFIG =====
PORT = "COM6"
BAUDRATE = 9600
TIMEOUT = 2

STX = 0x02
ETX = 0x03

HEADER_LEN = 6
DATA_LEN = 41
FRAME_LEN = 1 + HEADER_LEN + DATA_LEN + 1 + 1 + 1  # 50 bytes expected

# ===== USER FRAME (FULL FRAME: STX ... ETX BCC) =====
frame_hex = (
    "01 52 31 02 31 2E 30 2E 46 28 29 03 24"
)

# ===== INIT UART =====
ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)


# ===== BCC CHECK =====
def calc_bcc(frame):
    bcc = 0
    for b in frame[1:-1]:  # HEADER → ETX
        bcc ^= b
    return bcc


# ===== SEND =====
def send_frame():
    frame = bytes.fromhex(frame_hex)

    print("\n=== SENDING FRAME ===")
    print(frame.hex().upper())

    ser.write(frame)


# ===== READ =====
def read_frame():
    while True:
        b = ser.read(1)
        if not b:
            return None

        if b[0] == STX:
            rest = ser.read(FRAME_LEN - 1)
            if len(rest) == FRAME_LEN - 1:
                return b + rest


# ===== PARSE =====
def parse_frame(frame):
    header = frame[1:1+HEADER_LEN]
    data = frame[1+HEADER_LEN:1+HEADER_LEN+DATA_LEN]
    etx = frame[-2]
    bcc = frame[-1]

    # ETX check
    if etx != ETX:
        print("❌ Invalid ETX")
        return None

    # BCC check (optional, just warn)
    calc = calc_bcc(frame)
    if calc != bcc:
        print(f"⚠️ BCC mismatch: expected {bcc:02X}, got {calc:02X}")

    index = data[0]

    timestamps = []
    for i in range(10):
        chunk = data[1 + i*4 : 1 + (i+1)*4]
        ts = int.from_bytes(chunk, "big")
        timestamps.append(ts)

    return header, index, timestamps


# ===== PRINT =====
def print_table(index, timestamps):
    print("\n=== RESULT ===")
    print(f"Index: {index}\n")

    print(f"{'#':<3} {'HEX':<12} {'DEC':<12} {'GMT+7 TIME'}")
    print("-" * 50)

    for i, ts in enumerate(timestamps, 1):
        hex_str = f"{ts:08X}"

        if ts == 0xFFFFFFFF:
            time_str = "EMPTY"
        else:
            dt = datetime.fromtimestamp(ts, timezone.utc) + timedelta(hours=7)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        print(f"{i:<3} {hex_str:<12} {ts:<12} {time_str}")


# ===== MAIN =====
send_frame()

print("\nWaiting for response...")

frame = read_frame()

if frame:
    print("\n=== RECEIVED RAW ===")
    print(frame.hex().upper())

    result = parse_frame(frame)
    if result:
        header, index, timestamps = result
        print("Header:", header.hex().upper())
        print_table(index, timestamps)
    else:
        print("Frame parse failed")
else:
    print("No response")

ser.close()