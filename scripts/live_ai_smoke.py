"""Explicit synthetic, free-only inference. Does not enable real-data processing.

Reads the authorized key file into memory; never prints it or provider errors.
The selected model/upstream are arguments, so there is no silent fallback.
"""

import argparse
import base64
import hashlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import httpx  # noqa: E402
from schulpilot.fixtures import trusted_payload, worksheet  # noqa: E402
from schulpilot.providers import strict_schema, system_text  # noqa: E402
from schulpilot.schemas import ExtractionOutput, PackageOutput, UnitOutput  # noqa: E402

OCR_ROOT = Path(__file__).resolve().parents[1] / 'testdata' / 'ocr_synthetic'
OCR_FIXTURES = {
    'fraction': ('01_bruch_tabelle.png', 'b0306ab4a32c4a6471dc0b55b5a72d92d6492dbadf88887cb1dbfa47001c8fc2', 'image/png'),
    'occluded': ('02_deutsch_verdeckt.png', '0383ca1102c4451e7e59795b59b2268f64834bbf9c1d249fa2f5eddc5ffca1ad', 'image/png'),
    'water': ('03_wasser_schief.jpg', 'a7b5e4bd0cb8d029dad72e371bb54dead6095a5855fe611385b3ccb3db63459e', 'image/jpeg'),
    'handwritten': ('04_ki_bruchheft.png', '9593de1b643a39f310a1fd67c35e5f0f5c5b89f533b33770873777dd38829346', 'image/png'),
}


def fixed_ocr_fixture(name):
    """Only fixed, checksum-bound synthetic images can leave the workstation."""
    filename, expected, mime = OCR_FIXTURES[name]
    data = (OCR_ROOT / filename).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Synthetic fixture does not match its checked checksum')
    return data, mime


def provider_options(upstream, *, strict_privacy):
    return {
        'only': [upstream],
        'allow_fallbacks': False,
        'require_parameters': True,
        'data_collection': 'deny',
        'zdr': strict_privacy,
        'max_price': {'prompt': 0, 'completion': 0, 'request': 0},
    }


def verified_free_endpoint(data, upstream, *, image):
    if image and 'image' not in data.get('architecture', {}).get('input_modalities', []):
        raise ValueError('Selected model does not advertise image input')
    endpoint = next((e for e in data.get('endpoints', []) if e.get('tag') == upstream), None)
    if not endpoint or endpoint.get('status') != 0:
        raise ValueError('Selected endpoint is unavailable')
    prices = endpoint.get('pricing', {})
    if not isinstance(prices, dict) or not {'prompt', 'completion'} <= prices.keys():
        raise ValueError('Selected endpoint has incomplete pricing')
    try:
        if any(not Decimal(str(value)).is_finite() or Decimal(str(value)) != 0
               for key, value in prices.items() if key != 'discount'):
            raise ValueError('Selected endpoint is not verified free')
    except InvalidOperation as error:
        raise ValueError('Selected endpoint has invalid pricing') from error
    if not {'response_format', 'structured_outputs', 'max_tokens'} <= set(endpoint.get('supported_parameters', [])):
        raise ValueError('Selected endpoint does not advertise the required parameters')
    return endpoint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--upstream", required=True)
    parser.add_argument("--key-file", type=Path, default=Path.home() / "or.txt")
    parser.add_argument("--function", choices=["extract", "unit", "package"], default="extract")
    parser.add_argument("--ocr-fixture", choices=sorted(OCR_FIXTURES), help="Use one fixed checksum-bound synthetic OCR page")
    parser.add_argument("--strict-privacy", action="store_true", help="Probe deny + ZDR using synthetic data only")
    args = parser.parse_args()
    if not args.model.endswith(":free"):
        raise SystemExit("Only an explicitly selected :free model is permitted")
    if args.ocr_fixture and args.function != 'extract':
        parser.error('--ocr-fixture is only available for extraction')
    if args.ocr_fixture:
        image_data, image_mime = fixed_ocr_fixture(args.ocr_fixture)
    else:
        image_data, image_mime = (worksheet(), 'image/jpeg') if args.function == 'extract' else (None, None)
    model_type = {"extract": ExtractionOutput, "package": PackageOutput}.get(args.function, UnitOutput)
    with httpx.Client(timeout=150, follow_redirects=False) as client:
        metadata = client.get("https://openrouter.ai/api/v1/models/" + args.model + "/endpoints")
        metadata.raise_for_status()
        verified_free_endpoint(metadata.json()['data'], args.upstream, image=args.function == 'extract')
        payload = trusted_payload(args.function)
        if args.ocr_fixture:
            payload['synthetic_fixture'] = 'fixed-ocr-reference'
        content = [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]
        if args.function == "extract":
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_mime};base64," + base64.b64encode(image_data).decode()},
                }
            )
        body = {
            "model": args.model,
            "max_tokens": 7000,
            "messages": [
                {"role": "system", "content": system_text(args.function)},
                {"role": "user", "content": content},
            ],
            "provider": provider_options(args.upstream, strict_privacy=args.strict_privacy),
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "schulpilot", "strict": True, "schema": strict_schema(model_type)},
            },
            "reasoning": {"enabled": False},
        }
        response = client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": "Bearer " + args.key_file.read_text().strip()},
            json=body,
        )
        report = {
            "model": args.model,
            "upstream": args.upstream,
            "function": args.function,
            "http_status": response.status_code,
            "synthetic_only": True,
            "ocr_fixture": args.ocr_fixture,
            "strict_privacy": args.strict_privacy,
        }
        if response.status_code != 200:
            try:
                err = response.json().get("error", {})
                report["error_code"] = err.get("code")
                # Report only a short routing reason, never arbitrary upstream text.
                if "No endpoints" in str(err.get("message", "")):
                    report["reason"] = "No endpoints found matching routing requirements"
            except ValueError:
                pass
            print(json.dumps(report))
            raise SystemExit(1)
        raw = response.json()
        try:
            choice = raw["choices"][0]
            report["finish_reason"] = choice.get("finish_reason")
            if choice.get("finish_reason") != "stop":
                raise ValueError("incomplete")
            output = model_type.model_validate_json(choice["message"]["content"])
        except (ValueError, KeyError, TypeError, IndexError) as error:
            report["validated"] = False
            if hasattr(error, "errors"):
                report["validation_errors"] = [{"location": e["loc"], "message": e["msg"]} for e in error.errors()]
            report["synthetic_output"] = raw.get("choices", [{}])[0].get("message", {}).get("content", "")[:6000]
            report["usage"] = raw.get("usage", {})
            print(json.dumps(report))
            raise SystemExit(1)
        report["validated"] = True
        report["usage"] = raw.get("usage", {})
        report["data"] = output.model_dump()
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
