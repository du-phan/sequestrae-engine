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
    parse_pdfs_parser.add_argument("--llama-api-key", help="Llama API key", required=True)
    parse_pdfs_parser.add_argument("--project-dir", help="Project data directory", required=True)
    parse_pdfs_parser.add_argument("--limit", help="Maximum number of PDFs to process", type=int)
    parse_pdfs_parser.set_defaults(
        func=lambda args: commands.parse_pdfs_command(
            args.llama_api_key, args.project_dir, args.limit
        )
    )

    # Extract audit information command
    extract_audit_parser = subparsers.add_parser(
        "extract-audit", help="Extract audit information from markdown report files"
    )
    extract_audit_parser.add_argument("--mistral-api-key", help="Mistral API key", required=True)
    extract_audit_parser.add_argument("--project-dir", help="Project data directory", required=True)
    extract_audit_parser.add_argument(
        "--limit", help="Maximum number of files to process", type=int
    )
    extract_audit_parser.set_defaults(
        func=lambda args: commands.extract_audit_information_command(
            args.mistral_api_key, args.project_dir, args.limit
        )
    )

    # Evaluate feedstock sustainability command
    evaluate_feedstock_parser = subparsers.add_parser(
        "evaluate-feedstock", help="Evaluate feedstock sustainability from markdown report files"
    )
    evaluate_feedstock_parser.add_argument(
        "--mistral-api-key", help="Mistral API key", required=True
    )
    evaluate_feedstock_parser.add_argument(
        "--project-dir", help="Project data directory", required=True
    )
    evaluate_feedstock_parser.add_argument(
        "--limit", help="Maximum number of files to process", type=int
    )
    evaluate_feedstock_parser.set_defaults(
        func=lambda args: commands.evaluate_feedstock_sustainability_command(
            args.mistral_api_key, args.project_dir, args.limit
        )
    )

    # Populate feedstock evaluation table command
    populate_feedstock_parser = subparsers.add_parser(
        "populate-feedstock-table", help="Populate Supabase with feedstock evaluation data"
    )
    populate_feedstock_parser.add_argument("--supabase-url", help="Supabase URL", required=True)
    populate_feedstock_parser.add_argument("--supabase-api-key", help="Supabase key", required=True)
    populate_feedstock_parser.add_argument(
        "--project-dir", help="Project data directory", required=True
    )
    populate_feedstock_parser.set_defaults(
        func=lambda args: commands.populate_feedstock_evaluation_command(
            args.supabase_url, args.supabase_api_key, args.project_dir
        )
    )

    # Due diligence analyze command
    process_analyze_parser = subparsers.add_parser(
        "due-diligence-analyze",
        help="Process PDFs and analyze due diligence criteria for all projects",
    )
    process_analyze_parser.add_argument(
        "--gemini-api-key", help="Gemini API key for PDF parsing", required=True
    )
    process_analyze_parser.add_argument(
        "--mistral-api-key", help="Mistral API key for analysis", required=True
    )
    process_analyze_parser.add_argument(
        "--project-dir", help="Project data directory", required=True
    )
    process_analyze_parser.set_defaults(
        func=lambda args: commands.analyze_due_diligence_command(
            args.gemini_api_key, args.mistral_api_key, args.project_dir
        )
    )

    # Create subtopic summaries command
    create_summaries_parser = subparsers.add_parser(
        "create-subtopic-summaries", help="Create subtopic summaries from analysis JSON files"
    )
    create_summaries_parser.add_argument(
        "--mistral-api-key", help="Mistral API key for analysis", required=True
    )
    create_summaries_parser.add_argument(
        "--project-dir", help="Project data directory", required=True
    )
    create_summaries_parser.set_defaults(
        func=lambda args: commands.create_subtopic_summaries_command(
            args.mistral_api_key, args.project_dir
        )
    )

    # Create topic summaries command
    create_topic_parser = subparsers.add_parser(
        "create-topic-summaries", help="Create topic summaries from subtopic summary JSON files"
    )
    create_topic_parser.add_argument(
        "--mistral-api-key", help="Mistral API key for analysis", required=True
    )
    create_topic_parser.add_argument("--project-dir", help="Project data directory", required=True)
    create_topic_parser.set_defaults(
        func=lambda args: commands.create_topic_summaries_command(
            args.mistral_api_key, args.project_dir
        )
    )

    # Extract project overview command
    extract_overview_parser = subparsers.add_parser(
        "extract-project-overview", help="Extract project overview data from markdown documents"
    )
    extract_overview_parser.add_argument(
        "--mistral-api-key", help="Mistral API key for analysis", required=True
    )
    extract_overview_parser.add_argument(
        "--project-dir", help="Project data directory", required=True
    )
    extract_overview_parser.set_defaults(
        func=lambda args: commands.extract_project_overview_command(
            args.mistral_api_key, args.project_dir
        )
    )

    # Add new command for populating registry analysis data
    populate_registry_parser = subparsers.add_parser(
        "populate-registry-analysis",
        help="Populate Supabase with analysis data from multiple registry folders",
    )
    populate_registry_parser.add_argument("--supabase-url", help="Supabase URL", required=True)
    populate_registry_parser.add_argument("--supabase-api-key", help="Supabase key", required=True)
    populate_registry_parser.add_argument(
        "--registries-dir", help="Root directory containing registry folders", required=True
    )
    populate_registry_parser.set_defaults(
        func=lambda args: commands.populate_registry_analysis_command(
            args.supabase_url, args.supabase_api_key, args.registries_dir
        )
    )

    # Add new command for generating project main insights
    create_main_insights_parser = subparsers.add_parser(
        "create-project-insights", help="Create project main insights from topic summary JSON files"
    )
    create_main_insights_parser.add_argument(
        "--mistral-api-key", help="Mistral API key for analysis", required=True
    )
    create_main_insights_parser.add_argument(
        "--project-dir", help="Project data directory", required=True
    )
    create_main_insights_parser.set_defaults(
        func=lambda args: commands.create_project_main_insights_command(
            args.mistral_api_key, args.project_dir
        )
    )

    # Add new command for processing a single project through the entire pipeline
    process_project_parser = subparsers.add_parser(
        "process-project", help="Run the complete analysis pipeline for a single project folder"
    )
    process_project_parser.add_argument(
        "--gemini-api-key", help="Gemini API key for PDF parsing", required=True
    )
    process_project_parser.add_argument(
        "--mistral-api-key", help="Mistral API key for analysis", required=True
    )
    process_project_parser.add_argument(
        "--project-dir", help="Path to the specific project folder to process", required=True
    )
    process_project_parser.add_argument(
        "--overwrite", help="Overwrite existing output files", action="store_true"
    )
    process_project_parser.set_defaults(
        func=lambda args: commands.process_project_command(
            args.gemini_api_key, args.mistral_api_key, args.project_dir, args.overwrite
        )
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
