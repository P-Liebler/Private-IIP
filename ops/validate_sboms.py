"""Offline CycloneDX 1.7 schema validation bound to exact recorded SBOM hashes.

Tool-only dependency: jsonschema==4.26.0; never install into the model runtime.
"""
import argparse
import json
from pathlib import Path
from jsonschema.validators import validator_for
from referencing import Registry, Resource
from security_audit import sha256, write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    schemas = Path(__file__).with_name("security-schemas")
    registry = Registry()
    hashes = {}
    for path in schemas.glob("*.schema.json"):
        resource = Resource.from_contents(json.loads(path.read_text(encoding="utf-8")))
        hashes[path.name] = sha256(path)
        for scheme in ("http", "https"):
            registry = registry.with_resource(f"{scheme}://cyclonedx.org/schema/{path.name}", resource)
    schema = json.loads((schemas / "bom-1.7.schema.json").read_text(encoding="utf-8"))
    validator = validator_for(schema)(schema, registry=registry)
    value = json.loads(args.inventory.read_text(encoding="utf-8"))
    records = []
    for image in value["images"]:
        result = {"component": image["component"], "valid": False}
        try:
            path = args.inventory.parent / image["sbom_file"]
            if not path.resolve().is_relative_to(args.inventory.parent.resolve()) or sha256(path) != image["sbom_sha256"]:
                raise ValueError("SBOM_HASH_MISMATCH")
            errors = list(validator.iter_errors(json.loads(path.read_text(encoding="utf-8"))))
            result.update(valid=not errors, errors=[{"path": list(e.path), "keyword": e.validator} for e in errors])
        except (KeyError, OSError, ValueError):
            result["error"] = "SBOM_MISSING_OR_INVALID"
        records.append(result)
    passed = bool(records) and all(r["valid"] for r in records)
    write_new(args.output, {"schema_hashes": hashes, "validator": "jsonschema 4.26.0", "valid": passed, "records": records})
    print("SBOM_VALID" if passed else "SBOM_INVALID_OR_INCOMPLETE")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
