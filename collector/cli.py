#!/usr/bin/env python3
"""
MusicLive Collector CLI

Minimal implementation for parsing fixtures and testing extractors.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from collector.extractors.sample_venue import SampleVenueExtractor
from collector.extractors.music_farm import MusicFarmExtractor
from collector.extractors.base import ExtractResult
from db.persistence import get_connection, ensure_site, ensure_source, upsert_venue, insert_event_instance, upsert_event_source_link
from collector.intelligent_crawler import run_intelligent_crawl, discover_and_crawl_sources


def parse_html_file(file_path: str, site_slug: str, source_url: str) -> List[ExtractResult]:
    """Parse an HTML file using the appropriate extractor."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Choose extractor based on file path or content
        if "music_farm" in file_path:
            extractor = MusicFarmExtractor(site_slug=site_slug, source_url=source_url)
        else:
            extractor = SampleVenueExtractor(site_slug=site_slug, source_url=source_url)
        
        results = extractor.parse(html_content)
        return results
    except FileNotFoundError:
        print(f"Error: HTML file '{file_path}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing HTML: {e}", file=sys.stderr)
        sys.exit(1)


def format_output(results: List[ExtractResult], output_format: str) -> str:
    """Format the extraction results in the specified output format."""
    if output_format == "json":
        # Convert ExtractResult objects to dictionaries
        output_data = []
        for result in results:
            result_dict = {
                "site_slug": result.site_slug,
                "venue_name": result.venue_name,
                "title": result.title,
                "artist_name": result.artist_name,
                "starts_at_utc": result.starts_at_utc,
                "ends_at_utc": result.ends_at_utc,
                "tz_name": result.tz_name,
                "doors_time_utc": result.doors_time_utc,
                "price_min": result.price_min,
                "price_max": result.price_max,
                "currency": result.currency,
                "ticket_url": result.ticket_url,
                "age_restriction": result.age_restriction,
                "is_cancelled": result.is_cancelled,
                "source_url": result.source_url,
                "external_id": result.external_id,
                "raw_data": result.raw_data
            }
            output_data.append(result_dict)
        
        return json.dumps(output_data, indent=2, default=str)
    
    elif output_format == "summary":
        lines = [f"Extracted {len(results)} events:"]
        for i, result in enumerate(results, 1):
            lines.append(f"  {i}. {result.title}")
            lines.append(f"     Venue: {result.venue_name}")
            lines.append(f"     Date: {result.starts_at_utc}")
            if result.price_min:
                price_str = f"${result.price_min}"
                if result.price_max and result.price_max != result.price_min:
                    price_str += f" - ${result.price_max}"
                lines.append(f"     Price: {price_str}")
            lines.append("")
        return "\n".join(lines)
    
    else:
        raise ValueError(f"Unknown output format: {output_format}")


def ingest_to_db(html_file: str, site_slug: str, source_url: str, source_name: str) -> None:
    """Parse HTML fixture and ingest results to database."""
    print(f"🔄 Ingesting {html_file} to database...")
    
    # Parse the HTML
    results = parse_html_file(html_file, site_slug, source_url)
    print(f"📊 Parsed {len(results)} events")
    
    # Connect to database
    try:
        conn = get_connection()
    except Exception as e:
        print(f"❌ Database connection failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with conn.cursor() as cur:
            # Start transaction
            cur.execute("BEGIN")
            
            try:
                # Create ingest_run
                cur.execute(
                    """
                    INSERT INTO ingest_run (source_id, started_at, status)
                    VALUES (%s, now(), 'running')
                    RETURNING id
                    """,
                    (None,)  # We'll update this after creating the source
                )
                ingest_run_id = cur.fetchone()[0]
                print(f"📝 Created ingest_run: {ingest_run_id}")
                
                # Ensure site and source
                site_id = ensure_site(conn, site_slug)
                source_id = ensure_source(conn, site_id, source_name, source_url)
                
                # Update ingest_run with source_id
                cur.execute(
                    "UPDATE ingest_run SET source_id = %s WHERE id = %s",
                    (source_id, ingest_run_id)
                )
                
                print(f"🏗️ Ensured site: {site_id}, source: {source_id}")
                
                # Process each event
                for i, result in enumerate(results, 1):
                    print(f"  Processing event {i}/{len(results)}: {result.title}")
                    
                    # Upsert venue
                    venue_id = upsert_venue(
                        conn,
                        site_id,
                        result.venue_name,
                        tz_name=result.tz_name
                    )
                    
                    # Parse datetime strings to datetime objects
                    from datetime import datetime
                    starts_at = datetime.fromisoformat(result.starts_at_utc.replace('Z', '+00:00'))
                    ends_at = None
                    if result.ends_at_utc:
                        ends_at = datetime.fromisoformat(result.ends_at_utc.replace('Z', '+00:00'))
                    
                    # Insert event instance
                    event_id = insert_event_instance(
                        conn,
                        site_id,
                        venue_id,
                        title=result.title,
                        description=None,  # Not in ExtractResult yet
                        artist_name=result.artist_name,
                        starts_at_utc=starts_at,
                        ends_at_utc=ends_at,
                        tz_name=result.tz_name,
                        doors_time_utc=None,
                        price_min=result.price_min,
                        price_max=result.price_max,
                        currency=result.currency,
                        ticket_url=result.ticket_url,
                        age_restriction=result.age_restriction,
                        is_cancelled=result.is_cancelled,
                        source_created_at=None,
                        source_updated_at=None,
                    )
                    
                    # Upsert event source link
                    link_id = upsert_event_source_link(
                        conn,
                        event_instance_id=event_id,
                        source_id=source_id,
                        ingest_run_id=ingest_run_id,
                        external_id=result.external_id,
                        source_url=result.source_url,
                        raw_data=result.raw_data,
                    )
                    
                    print(f"    ✅ Event {event_id}, venue {venue_id}, link {link_id}")
                
                # Complete ingest_run
                cur.execute(
                    "UPDATE ingest_run SET status = 'completed', finished_at = now() WHERE id = %s",
                    (ingest_run_id,)
                )
                
                # Commit transaction
                cur.execute("COMMIT")
                print(f"🎉 Successfully ingested {len(results)} events to database")
                print(f"📊 Ingest run {ingest_run_id} completed successfully")
                
            except Exception as e:
                # Rollback on error
                cur.execute("ROLLBACK")
                print(f"❌ Error during ingestion: {e}", file=sys.stderr)
                
                # Update ingest_run status to failed
                try:
                    cur.execute(
                        "UPDATE ingest_run SET status = 'failed', finished_at = now() WHERE id = %s",
                        (ingest_run_id,)
                    )
                    conn.commit()
                except:
                    pass  # Best effort to update status
                
                raise
    
    finally:
        conn.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MusicLive Collector CLI - Parse HTML fixtures and extract events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse the sample venue fixture
  poetry run collector parse tests/fixtures/sample_venue/event_page.html --site charleston --source "https://example.com/sample-venue/events"
  
  # Output as summary instead of JSON
  poetry run collector parse tests/fixtures/sample_venue/event_page.html --site charleston --format summary
  
  # Ingest fixture to database
  poetry run collector ingest tests/fixtures/sample_venue/event_page.html --site charleston --source "https://example.com/sample-venue/events" --source-name "Sample Venue"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse HTML file and extract events')
    parse_parser.add_argument('html_file', help='Path to HTML file to parse')
    parse_parser.add_argument('--site', required=True, help='Site slug (e.g., charleston)')
    parse_parser.add_argument('--source', required=True, help='Source URL for attribution')
    parse_parser.add_argument('--format', choices=['json', 'summary'], default='json',
                            help='Output format (default: json)')
    
    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Parse HTML file and ingest to database')
    ingest_parser.add_argument('html_file', help='Path to HTML file to parse and ingest')
    ingest_parser.add_argument('--site', required=True, help='Site slug (e.g., charleston)')
    ingest_parser.add_argument('--source', required=True, help='Source URL for attribution')
    ingest_parser.add_argument('--source-name', required=True, help='Source name for database')
    
    # Discover command
    discover_parser = subparsers.add_parser('discover', help='Intelligently discover and crawl event sources')
    discover_parser.add_argument('--site', required=True, help='Site slug (e.g., charleston)')
    discover_parser.add_argument('--city', required=True, help='City name (e.g., Charleston)')
    discover_parser.add_argument('--state', required=True, help='State abbreviation (e.g., SC)')
    discover_parser.add_argument('--max-sources', type=int, default=20, help='Maximum number of sources to crawl (default: 20)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'parse':
        # Parse the HTML file
        results = parse_html_file(args.html_file, args.site, args.source)
        
        # Format and output results
        try:
            output = format_output(results, args.format)
            print(output)
        except Exception as e:
            print(f"Error formatting output: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'ingest':
        # Ingest to database
        ingest_to_db(args.html_file, args.site, args.source, args.source_name)
    
    elif args.command == 'discover':
        # Discover and crawl sources intelligently
        import asyncio
        asyncio.run(discover_and_crawl_sources(args.site, args.city, args.state, args.max_sources))


if __name__ == '__main__':
    main()
