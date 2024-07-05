# Temporary tests. Dismiss. Safe to delete.
import crcmod

#Commands with CRC cheats
QPGS = '\x51\x50\x47\x53\x30\x3f\xda\x0d'
QPIGS = '\x51\x50\x49\x47\x53\xB7\xA9\x0d'
QMCHGCR ='\x51\x4D\x43\x48\x47\x43\x52\xD8\x55\x0D' #?
QMUCHGCR='\x51\x4D\x55\x43\x48\x47\x43\x52\x26\x34 \x0D' #?
QPIWS = '\x51\x50\x49\x57\x53\xB4\xDA\x0D' #valid?
POP02 = '\x50\x4F\x50\x30\x32\xE2\x0B\x0D' # set to SBU
POP00 = '\x50\x4F\x50\x30\x30\xC2\x48\x0D' #Set to UTILITY
QMOD  = '\x51\x4D\x4F\x44\x49\xC1\x0d' 
#"QMOD\x49\xC1";
#"QID\xD6\xEA";
#"QVFW\x62\x99";
#"QVFW2\xC3\xF5";
#"QPIRI\xF8\x54"; -->51 50 49 52 49
#QPIRI = '\x51\x50\x49\x52\x49\xF8\x54\x0D'
#"QFLAG\x98\x74";

xmodem_crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)

def calculate_checksum(command):
    # Sum the ASCII values of all characters in the command
    checksum = sum(ord(c) for c in command)
    # Convert the sum to a 2-byte representation
    checksum_bytes = checksum.to_bytes(2, 'big')
    return checksum_bytes

def calculate_crc(command):
    crc_value = xmodem_crc_func(command)
    crc_hex = hex(crc_value)[2:].zfill(4)  # Get the CRC value in hexadecimal and pad with zeros if needed
    crc1 = int(crc_hex[0:2], 16)
    crc2 = int(crc_hex[2:4], 16)
    return crc1, crc2

def encode_command(command):
    # Calculate CRC
    crc1, crc2 = calculate_crc(command)
    # Append CRC and carriage return to the command
    encoded_command = command + bytes([crc1, crc2]) + b'\r'
    return encoded_command



# Example usage for QPIGS
#QPIGS_command = b'\x51\x50\x49\x47\x53'
#encoded_QPIGS = encode_command(QPIGS_command)
#print(encoded_QPIGS)  # Expected output: b'QPIGS\xb7\xa9\r'

# Example usage for QMOD
QMOD_command = b'\x51\x4D\x4F\x44'
encoded_QMOD = encode_command(QMOD_command)
print(encoded_QMOD)  # Expected output: b'QMOD\xYY\xZZ\r' (with correct checksum bytes)