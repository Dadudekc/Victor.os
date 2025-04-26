#!/usr/bin/env python3
import json
from pathlib import Path

def dedupe_and_chunk(input_file: str, chunk_size: int = 400, output_dir: str = "chunks"):
    # Load the full task list
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Deduplicate by description
    seen = set()
    unique = []
    for item in data:
        desc = item.get("description")
        if desc not in seen:
            seen.add(desc)
            unique.append(item)

    # Prepare output directory
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Chunk and write out
    total = len(unique)
    num_chunks = (total + chunk_size - 1) // chunk_size
    for i in range(num_chunks):
        chunk = unique[i*chunk_size : (i+1)*chunk_size]
        chunk_file = out_path / f"master_task_list_chunk_{i+1}.json"
        with open(chunk_file, "w", encoding="utf-8") as cf:
            json.dump(chunk, cf, indent=2)
        print(f"Wrote chunk {i+1}/{num_chunks}: {len(chunk)} entries → {chunk_file}")

    # Summary
    print(f"\nOriginal entries: {len(data)}")
    print(f"Unique entries:   {len(unique)}")
    print(f"Chunks created:   {num_chunks}")

if __name__ == "__main__":
    dedupe_and_chunk("master_task_list.json", chunk_size=400, output_dir="chunks") 
