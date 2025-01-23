import base64


def int_to_base64(num):
    num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
    encoded = base64.b64encode(num_bytes).decode('utf-8')
    return encoded


def base64_to_int(encoded):
    num_bytes = base64.b64decode(encoded)
    num = int.from_bytes(num_bytes, byteorder='big')
    return num
