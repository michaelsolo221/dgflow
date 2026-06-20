#!/usr/bin/env python3
"""Seed the Firestore personas collection with Luna, Viktor, and Sol."""

import argparse
import json
import sys
from pathlib import Path

from google.cloud import firestore


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Firestore personas collection")
    parser.add_argument("--project-id", required=True, help="GCP project ID")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    personas_path = repo_root / "firestore" / "personas.json"

    try:
        with open(personas_path) as f:
            personas = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error reading {personas_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        db = firestore.Client(project=args.project_id)
    except Exception as exc:
        print(f"Error connecting to Firestore: {exc}", file=sys.stderr)
        sys.exit(1)

    for persona_id, data in personas.items():
        try:
            doc_ref = db.collection("personas").document(persona_id)
            doc_ref.set(data, merge=True)
            print(f"Seeded: {data.get('display_name', persona_id)}")
        except Exception as exc:
            print(f"Error seeding {persona_id}: {exc}", file=sys.stderr)
            sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
