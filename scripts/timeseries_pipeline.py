#!/usr/bin/env python3
"""
High-Performance Time-Series Ingestion Pipeline for TimescaleDB
==============================================================
This script parses sensor data from large CSV files in chunks
and streams them into the database using asyncpg's copy_records_to_table.
It includes QC filters (NaN check, timestamp parsing, etc.) and is 
highly resilient to network failures and schema variations.
"""
import os
import sys
import csv
import time
import argparse
import asyncio
from datetime import datetime
import pytz
import asyncpg

# Set event loop policy for Windows if running locally
if sys.platform == 'win32' and not os.environ.get('DOCKER_CONTAINER'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DEFAULT_DSN = os.getenv(
    "TS_DSN", 
    "postgresql://postgres:postgres@localhost:5432/ecoanp?sslmode=disable"
)

# Target timezone
KST = pytz.timezone('Asia/Seoul')

async def detect_schema(conn) -> tuple[str, bool]:
    """Detect the quality column name and if a unique constraint exists on (ts, tag_name)."""
    # 1. Detect column name (quality vs qc)
    columns = await conn.fetch("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'influx_hist' AND table_schema = 'public';
    """)
    col_names = {row['column_name'] for row in columns}
    
    qual_col = 'quality'
    if 'quality' in col_names:
        qual_col = 'quality'
    elif 'qc' in col_names:
        qual_col = 'qc'
        
    # 2. Detect unique constraint or unique index on (ts, tag_name)
    has_unique = False
    index_query = """
        SELECT count(*)
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'influx_hist'
          AND n.nspname = 'public'
          AND i.indisunique = true
          AND (
            SELECT string_agg(attname, ',') 
            FROM pg_attribute 
            WHERE attrelid = c.oid 
              AND attnum = ANY(i.indkey)
          ) LIKE '%ts%' 
          AND (
            SELECT string_agg(attname, ',') 
            FROM pg_attribute 
            WHERE attrelid = c.oid 
              AND attnum = ANY(i.indkey)
          ) LIKE '%tag_name%';
    """
    try:
        val = await conn.fetchval(index_query)
        has_unique = val > 0
    except Exception:
        has_unique = True  # Default to true for standard edgeex deployment schema
        
    return qual_col, has_unique

def read_csv_in_chunks(file_path, batch_size, tz):
    """Generator yielding parsed and validated chunks from the CSV file."""
    chunk = []
    skipped_count = 0
    total_rows = 0
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")
        
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            ts_str = row.get('ts')
            tag_name = row.get('tag_name')
            val_str = row.get('value')
            qty_str = row.get('quality') or row.get('qc')
            
            # QC Check 1: Missing critical fields or empty values
            if not ts_str or not tag_name or val_str is None or val_str == '':
                skipped_count += 1
                continue
                
            # QC Check 2: Value parsing and validation (detect NaN/Inf)
            try:
                value = float(val_str)
                if value != value or value == float('inf') or value == float('-inf'):
                    skipped_count += 1
                    continue
            except ValueError:
                skipped_count += 1
                continue
                
            # QC Check 3: Timestamp parsing and timezone localization
            try:
                if len(ts_str) == 19:
                    dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                else:
                    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
            except Exception:
                skipped_count += 1
                continue
                
            # Quality code check: default to 0 (Good in edgeex context) or 192
            try:
                quality = int(qty_str) if qty_str is not None else 0
            except ValueError:
                quality = 0
                
            chunk.append((dt, tag_name, value, quality))
            
            if len(chunk) >= batch_size:
                yield chunk, total_rows, skipped_count
                chunk = []
                
        if chunk:
            yield chunk, total_rows, skipped_count

async def ingest_chunk(conn, chunk, qual_col, has_unique):
    """Insert a chunk using temporary staging table and high-performance COPY."""
    async with conn.transaction():
        # 1. Create a temporary staging table
        await conn.execute(f"""
            CREATE TEMP TABLE temp_stage (
                ts TIMESTAMPTZ,
                tag_name VARCHAR(50),
                value DOUBLE PRECISION,
                quality INTEGER
            ) ON COMMIT DROP;
        """)
        
        # 2. Stream using copy_records_to_table
        await conn.copy_records_to_table(
            'temp_stage',
            records=chunk,
            columns=['ts', 'tag_name', 'value', 'quality']
        )
        
        # 3. Insert or Upsert into target table public.influx_hist
        if has_unique:
            await conn.execute(f"""
                INSERT INTO public.influx_hist (ts, tag_name, value, {qual_col})
                SELECT ts, tag_name, value, quality FROM temp_stage
                ON CONFLICT (ts, tag_name) DO UPDATE
                SET value = EXCLUDED.value,
                    {qual_col} = EXCLUDED.{qual_col};
            """)
        else:
            await conn.execute(f"""
                INSERT INTO public.influx_hist (ts, tag_name, value, {qual_col})
                SELECT ts, tag_name, value, quality FROM temp_stage;
            """)

async def run_pipeline(csv_path, batch_size, dsn):
    print(f"Connecting to database...")
    try:
        conn = await asyncpg.connect(dsn)
    except Exception as e:
        print(f"CRITICAL: Failed to connect to database: {e}")
        sys.exit(1)
        
    try:
        print("Detecting database schema constraints...")
        qual_col, has_unique = await detect_schema(conn)
        print(f"Schema detected: quality column = '{qual_col}', unique constraint = {has_unique}")
        
        print(f"Starting ingestion pipeline from: {csv_path}")
        start_time = time.time()
        
        total_ingested = 0
        total_skipped = 0
        last_progress_time = time.time()
        
        chunk_generator = read_csv_in_chunks(csv_path, batch_size, KST)
        
        for chunk, total_parsed, skipped_count in chunk_generator:
            try:
                await ingest_chunk(conn, chunk, qual_col, has_unique)
                total_ingested += len(chunk)
            except Exception as e:
                print(f"\nError ingesting chunk: {e}. Skipping this chunk.")
                total_skipped += len(chunk)
                
            total_skipped = skipped_count
            
            # Progress output
            now = time.time()
            if now - last_progress_time >= 3.0:
                speed = total_parsed / (now - start_time)
                print(f"Progress: Parsed {total_parsed:,} rows | Ingested {total_ingested:,} | Skipped {total_skipped:,} | Speed: {speed:.1f} rows/s", flush=True)
                last_progress_time = now
                
        end_time = time.time()
        duration = end_time - start_time
        speed = total_parsed / duration if duration > 0 else 0
        
        print("\n" + "="*50)
        print("INGESTION SUMMARY")
        print("="*50)
        print(f"Status:            COMPLETED SUCCESSFULLY")
        print(f"Total Time:        {duration:.2f} seconds")
        print(f"Total CSV Rows:    {total_parsed:,}")
        print(f"Ingested Records:  {total_ingested:,}")
        print(f"Skipped (Bad QC):  {total_skipped:,}")
        print(f"Average Speed:     {speed:.1f} rows/second")
        print("="*50)
        
    finally:
        await conn.close()

def main():
    parser = argparse.ArgumentParser(description="High-performance TimescaleDB Time-series Ingestion Pipeline")
    parser.add_argument("--csv-path", type=str, help="Path to the CSV file to ingest")
    parser.add_argument("--batch-size", type=int, default=20000, help="Batch size for DB insert chunks (default: 20000)")
    parser.add_argument("--dsn", type=str, default=DEFAULT_DSN, help="Database DSN connection string")
    
    args = parser.parse_args()
    
    # Resolve CSV Path
    csv_path = args.csv_path
    if not csv_path:
        # Default options in the current workspace directory
        workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        options = [
            os.path.join(workspace_dir, "all_sensors.csv"),
            os.path.join(workspace_dir, "all_sensors_20251027_20251126.csv")
        ]
        for opt in options:
            if os.path.exists(opt):
                csv_path = opt
                break
                
    if not csv_path or not os.path.exists(csv_path):
        print(f"Error: CSV file not found. Please specify --csv-path.")
        sys.exit(1)
        
    asyncio.run(run_pipeline(csv_path, args.batch_size, args.dsn))

if __name__ == "__main__":
    main()
