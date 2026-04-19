# zstd
import zstandard
# compression
def compress(f, level=2):
    return zstandard.compress(f, level=level)
# decompression
def decompress(f):
    return zstandard.decompress(f)

