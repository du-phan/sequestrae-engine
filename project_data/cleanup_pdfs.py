import os
import sys
from pathlib import Path


def remove_empty_folders(path: Path):
    for folder in sorted([x for x in path.glob("**/*") if x.is_dir()], reverse=True):
        try:
            folder.rmdir()  # Will only succeed if folder is empty
            print(f"Removed empty folder: {folder.relative_to(path)}")
        except OSError:  # Folder not empty
            pass


def cleanup_reports():
    # Get script location and build parent directory path
    base_dir = Path(__file__).resolve().parent

    if not base_dir.exists():
        print(f"Error: Directory not found at {base_dir}")
        sys.exit(1)

    # Process files
    total_files = 0
    removed_files = 0

    # Find and process PDF files
    for pdf_file in base_dir.rglob("*.pdf"):
        total_files += 1
        if "report" not in pdf_file.stem.lower():
            try:
                pdf_file.unlink()
                print(f"Removed file: {pdf_file.relative_to(base_dir)}")
                removed_files += 1
            except OSError as e:
                print(f"Error removing {pdf_file.relative_to(base_dir)}: {e}")

    # Clean up empty folders
    remove_empty_folders(base_dir)

    # Summary
    print(f"\nSummary:")
    print(f"Total PDFs found: {total_files}")
    print(f"Files removed: {removed_files}")
    print(f"Files kept: {total_files - removed_files}")


if __name__ == "__main__":
    cleanup_reports()
