"""아이콘 생성 스크립트 - 한 번만 실행하면 됩니다."""
import struct
import zlib

def create_png(width, height, pixels):
    """간단한 PNG 파일 생성 (외부 라이브러리 없이)"""
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    raw = b""
    for y in range(height):
        raw += b"\x00"  # filter none
        for x in range(width):
            r, g, b, a = pixels[y * width + x]
            raw += struct.pack("BBBB", r, g, b, a)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw)

    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")

def make_icon(size):
    pixels = []
    center = size / 2
    radius = size / 2 - 1

    for y in range(size):
        for x in range(size):
            dx = x - center + 0.5
            dy = y - center + 0.5
            dist = (dx * dx + dy * dy) ** 0.5

            if dist <= radius:
                # 빨간 원 (YouTube 느낌)
                r, g, b = 204, 0, 0

                # 흰색 재생 삼각형
                tri_cx = center - size * 0.05
                tri_size = size * 0.25
                # 삼각형 영역 판정
                rel_x = x - tri_cx
                rel_y = y - center
                if (rel_x > -tri_size * 0.4 and
                    rel_x < tri_size * 0.8 and
                    abs(rel_y) < tri_size * 0.7 * (1 - (rel_x + tri_size * 0.4) / (tri_size * 1.2))):
                    r, g, b = 255, 255, 255

                # 엣지 안티앨리어싱
                alpha = 255
                if dist > radius - 1:
                    alpha = max(0, min(255, int(255 * (radius - dist + 1))))

                pixels.append((r, g, b, alpha))
            else:
                pixels.append((0, 0, 0, 0))

    return create_png(size, size, pixels)

# 48x48, 128x128 아이콘 생성
for size, name in [(48, "icon48.png"), (128, "icon128.png")]:
    data = make_icon(size)
    with open(name, "wb") as f:
        f.write(data)
    print(f"{name} 생성 완료 ({len(data)} bytes)")
