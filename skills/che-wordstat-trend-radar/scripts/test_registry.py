#!/usr/bin/env python3
import copy
import importlib.util
import json
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("validate_registry", HERE / "validate_registry.py")
import sys
sys.modules["validate_registry"] = VALIDATOR
BUILDER = load_module("build_seed_manifest", HERE / "build_seed_manifest.py")


def template():
    return json.loads((ROOT / "assets" / "project-registry.template.json").read_text(encoding="utf-8"))


class RegistryTests(unittest.TestCase):
    def test_template_structure_is_valid_draft(self):
        errors, warnings = VALIDATOR.validate_registry(template())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_draft_cannot_build_production_manifest(self):
        errors, _ = VALIDATOR.validate_registry(template(), require_confirmed=True)
        self.assertIn("REGISTRY_NOT_CONFIRMED", errors)
        with self.assertRaises(ValueError):
            BUILDER.build_manifest(template())

    def test_confirmed_manifest_is_deterministic_and_deduplicated(self):
        data = template()
        data["project"]["registry_status"] = "confirmed"
        data["customer_jobs"][0]["seed_phrases"].append("  НАЗВАНИЕ   ПРОДУКТА ")
        first = BUILDER.build_manifest(data)
        second = BUILDER.build_manifest(copy.deepcopy(data))
        self.assertEqual(first, second)
        phrases = [x["phrase"] for x in first["seeds"]]
        self.assertEqual(len(phrases), len(set(phrases)))
        shared = next(x for x in first["seeds"] if x["phrase"] == "название продукта")
        self.assertGreaterEqual(len(shared["source_refs"]), 2)

    def test_bad_reference_is_rejected(self):
        data = template()
        data["customer_jobs"][0]["product_ids"] = ["product:missing"]
        errors, _ = VALIDATOR.validate_registry(data)
        self.assertTrue(any(x.startswith("UNKNOWN_PRODUCT_REF") for x in errors))

    def test_duplicate_id_is_rejected(self):
        data = template()
        data["audiences"][0]["id"] = data["products_services"][0]["id"]
        errors, _ = VALIDATOR.validate_registry(data)
        self.assertTrue(any(x.startswith("DUPLICATE_ID") for x in errors))


if __name__ == "__main__":
    unittest.main()
