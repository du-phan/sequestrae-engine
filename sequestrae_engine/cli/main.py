import argparse
import os
import sys

from . import commands


def main():
    parser = argparse.ArgumentParser(description="Sequestrae Engine CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Parse PDFs command
    parse_pdfs_parser = subparsers.add_parser(
        "parse-pdf", help="Parse PDF audit report files to Markdown"
    )
    parse_pdfs_parser.add_argument(
        "--api-key", help="Llama API key", default=os.environ.get("LLAMA_API_KEY")
    )
    parse_pdfs_parser.add_argument("--project-dir", help="Project data directory", required=True)
    parse_pdfs_parser.add_argument("--limit", help="Maximum number of PDFs to process", type=int)
    parse_pdfs_parser.set_defaults(
        func=lambda args: commands.parse_pdfs_command(args.api_key, args.project_dir, args.limit)
    )

    args = parser.parse_args()
    if hasattr(args, "func"):
        exit_status = args.func(args)
    else:
        parser.print_help()
        exit_status = 1
    return exit_status


if __name__ == "__main__":
    main()
