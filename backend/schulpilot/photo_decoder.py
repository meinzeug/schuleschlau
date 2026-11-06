"""Single-photo helper process: bounded memory, no credentials or network.

Protocol: four-byte big-endian JSON length, JSON, then sanitized JPEG bytes.
This script is executed directly with an empty environment, not as a service.
"""
import io
import json
import resource
import sys

# Linux service policy: the decoder may fail safely instead of taking down the
# 350 MiB API. Address space is stricter than resident memory and includes libs.
_MAX_ADDRESS = 210 * 1024 * 1024
_MAX_OUTPUT = 11 * 1024 * 1024
resource.setrlimit(resource.RLIMIT_AS, (_MAX_ADDRESS, _MAX_ADDRESS))
resource.setrlimit(resource.RLIMIT_FSIZE, (_MAX_OUTPUT, _MAX_OUTPUT))
resource.setrlimit(resource.RLIMIT_CPU, (25, 25))

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError  # noqa: E402

Image.MAX_IMAGE_PIXELS = 16_000_000


def response(meta, content=b''):
    encoded = json.dumps(meta, ensure_ascii=True, separators=(',', ':')).encode('ascii')
    if len(encoded) > 4096:
        raise RuntimeError('Decoder metadata too large')
    sys.stdout.buffer.write(len(encoded).to_bytes(4, 'big'))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.write(content)
    sys.stdout.buffer.flush()


def decode(raw):
    with Image.open(io.BytesIO(raw)) as source:
        if source.format not in ('JPEG', 'PNG', 'WEBP') or source.width * source.height > Image.MAX_IMAGE_PIXELS:
            raise ValueError('format or dimensions')
        geometry = {'input_width': source.width, 'input_height': source.height, 'input_bytes': len(raw)}
        ImageOps.exif_transpose(source, in_place=True)
        if source.mode == 'RGB':
            image = source
        else:
            image = source.convert('RGB')
            # The converted image owns its pixels. Release the original (which
            # can be a full 16-MP RGBA buffer) before resizing/encoding.
            source.close()
        image.thumbnail((3200, 3200))
        width, height = image.size
        warnings = []
        if min(image.size) < 600:
            warnings.append('Das Foto ist klein. Bitte prüfen, ob der Text gut lesbar ist.')
        # Encode before shrinking the same image for the clarity probe; this
        # preserves the original output and thumbnail algorithm without keeping
        # a second complete 3200-pixel buffer alive.
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=95)
        content = output.getvalue()
        if len(content) > 10 * 1024 * 1024:
            return {'status': 'output_too_large'}, b''
        image.thumbnail((320, 320))
        probe = image.convert('L').filter(ImageFilter.FIND_EDGES)
        if min(probe.size) > 4 and ImageStat.Stat(probe.crop((2, 2, probe.width - 2, probe.height - 2))).var[0] < 70:
            warnings.append('Das Foto enthält wenig erkennbare Details und könnte unscharf oder leer sein. Bitte prüfen.')
        geometry.update(width=width, height=height, output_bytes=len(content), orientation='baked')
        return {'status': 'ok', 'geometry': geometry, 'warnings': warnings}, content


def main():
    try:
        raw = sys.stdin.buffer.read(10 * 1024 * 1024 + 1)
        if len(raw) > 10 * 1024 * 1024:
            return response({'status': 'input_too_large'})
        meta, content = decode(raw)
        return response(meta, content)
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
        return response({'status': 'invalid'})
    except MemoryError:
        return response({'status': 'resource_limit'})
    except Exception:
        return response({'status': 'failure'})


if __name__ == '__main__':
    main()
