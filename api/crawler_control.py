"""
Crawler Control Web Interface

Provides a simple web interface for monitoring and controlling the intelligent crawler.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import logging
from datetime import datetime
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collector.intelligent_crawler import IntelligentCrawler, discover_and_crawl_sources
from db.persistence import get_connection
from config import DATABASE_URL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MusicLive Crawler Control", version="1.0.0")

# Global state for tracking crawler status
crawler_status = {
    'is_running': False,
    'current_session': None,
    'last_run': None,
    'total_runs': 0,
    'successful_runs': 0,
    'failed_runs': 0,
    'current_progress': {
        'phase': 'idle',
        'sources_discovered': 0,
        'sources_crawled': 0,
        'total_sources': 0,
        'events_found': 0,
        'artists_researched': 0,
        'current_source': None,
        'start_time': None,
        'estimated_completion': None
    }
}

class CrawlRequest(BaseModel):
    site_slug: str = "charleston"
    city: str = "Charleston"
    state: str = "SC"
    max_sources: int = 10

class CrawlResponse(BaseModel):
    status: str
    message: str
    session_id: Optional[str] = None
    estimated_duration: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Main dashboard for crawler control."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MusicLive Crawler Control</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .status-card { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .control-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
            .control-card { background: #e9ecef; padding: 20px; border-radius: 8px; }
            .btn { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #0056b3; }
            .btn:disabled { background: #6c757d; cursor: not-allowed; }
            .btn-danger { background: #dc3545; }
            .btn-danger:hover { background: #c82333; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: #fff; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #dee2e6; }
            .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
            .stat-label { color: #6c757d; margin-top: 5px; }
            .log-container { background: #f8f9fa; padding: 20px; border-radius: 8px; max-height: 400px; overflow-y: auto; }
            .log-entry { margin: 5px 0; padding: 5px; border-left: 3px solid #007bff; background: white; }
            .log-time { color: #6c757d; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎵 MusicLive Crawler Control</h1>
                <p>Monitor and control the intelligent event discovery system</p>
            </div>
            
            <div class="status-card">
                <h3>🔄 Crawler Status</h3>
                <div id="status-display">Loading...</div>
            </div>
            
            <div class="control-panel">
                <div class="control-card">
                    <h3>🚀 Start Crawl</h3>
                    <form id="crawl-form">
                        <div style="margin-bottom: 15px;">
                            <label>Site Slug:</label><br>
                            <input type="text" id="site-slug" value="charleston" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label>City:</label><br>
                            <input type="text" id="city" value="Charleston" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label>State:</label><br>
                            <input type="text" id="state" value="SC" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label>Max Sources:</label><br>
                            <input type="number" id="max-sources" value="10" min="1" max="50" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        <button type="submit" class="btn" id="start-btn">Start Crawl</button>
                    </form>
                </div>
                
                <div class="control-card">
                    <h3>⏹️ Stop Crawl</h3>
                    <p>Stop the currently running crawl operation.</p>
                    <button class="btn btn-danger" id="stop-btn" onclick="stopCrawl()">Stop Crawl</button>
                    
                    <h4 style="margin-top: 20px;">📊 Quick Stats</h4>
                    <button class="btn" onclick="refreshStats()">Refresh Stats</button>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-venues">-</div>
                    <div class="stat-label">Total Venues</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-events">-</div>
                    <div class="stat-label">Total Events</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-artists">-</div>
                    <div class="stat-label">Total Artists</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-sources">-</div>
                    <div class="stat-label">Total Sources</div>
                </div>
            </div>
            
            <div class="log-container">
                <h3>📝 Activity Log</h3>
                <div id="log-entries">
                    <div class="log-entry">
                        <span class="log-time">System ready</span>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let isRunning = false;
            
            // Update status display
            function updateStatus() {
                fetch('/api/status')
                    .then(response => response.json())
                    .then(data => {
                        const statusDisplay = document.getElementById('status-display');
                        const startBtn = document.getElementById('start-btn');
                        const stopBtn = document.getElementById('stop-btn');
                        
                        isRunning = data.is_running;
                        
                        if (data.is_running) {
                            statusDisplay.innerHTML = '<span style="color: #28a745;">🟢 Running</span> - Crawl in progress...';
                            startBtn.disabled = true;
                            stopBtn.disabled = false;
                        } else {
                            statusDisplay.innerHTML = '<span style="color: #6c757d;">⚪ Stopped</span> - Ready to start';
                            startBtn.disabled = false;
                            stopBtn.disabled = true;
                        }
                        
                        if (data.last_run) {
                            statusDisplay.innerHTML += '<br><small>Last run: ' + new Date(data.last_run).toLocaleString() + '</small>';
                        }
                    });
            }
            
            // Start crawl
            document.getElementById('crawl-form').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const data = {
                    site_slug: document.getElementById('site-slug').value,
                    city: document.getElementById('city').value,
                    state: document.getElementById('state').value,
                    max_sources: parseInt(document.getElementById('max-sources').value)
                };
                
                fetch('/api/crawl', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                })
                .then(response => response.json())
                .then(data => {
                    addLogEntry('Started crawl: ' + data.message);
                    updateStatus();
                })
                .catch(error => {
                    addLogEntry('Error starting crawl: ' + error.message);
                });
            });
            
            // Stop crawl
            function stopCrawl() {
                fetch('/api/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    addLogEntry('Stopped crawl: ' + data.message);
                    updateStatus();
                })
                .catch(error => {
                    addLogEntry('Error stopping crawl: ' + error.message);
                });
            }
            
            // Refresh stats
            function refreshStats() {
                fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('total-venues').textContent = data.total_venues;
                    document.getElementById('total-events').textContent = data.total_events;
                    document.getElementById('total-artists').textContent = data.total_artists;
                    document.getElementById('total-sources').textContent = data.total_sources;
                });
            }
            
            // Add log entry
            function addLogEntry(message) {
                const logContainer = document.getElementById('log-entries');
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                entry.innerHTML = '<span class="log-time">' + new Date().toLocaleTimeString() + '</span> ' + message;
                logContainer.appendChild(entry);
                logContainer.scrollTop = logContainer.scrollHeight;
            }
            
            // Auto-refresh
            setInterval(updateStatus, 5000);
            setInterval(refreshStats, 10000);
            
            // Initial load
            updateStatus();
            refreshStats();
        </script>
    </body>
    </html>
    """
    return html

@app.get("/api/status")
async def get_status():
    """Get current crawler status."""
    return crawler_status

@app.post("/api/crawl", response_model=CrawlResponse)
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """Start a new crawl operation."""
    if crawler_status['is_running']:
        raise HTTPException(status_code=400, detail="Crawler is already running")
    
    try:
        # Start crawl in background
        background_tasks.add_task(
            run_crawl_background,
            request.site_slug,
            request.city,
            request.state,
            request.max_sources
        )
        
        crawler_status['is_running'] = True
        crawler_status['total_runs'] += 1
        
        return CrawlResponse(
            status="started",
            message=f"Started crawl for {request.city}, {request.state}",
            estimated_duration="5-15 minutes"
        )
        
    except Exception as e:
        logger.error(f"Error starting crawl: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
async def stop_crawl():
    """Stop the currently running crawl."""
    if not crawler_status['is_running']:
        return {"status": "stopped", "message": "No crawl running"}
    
    crawler_status['is_running'] = False
    return {"status": "stopped", "message": "Crawl stopped"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        os.environ['DATABASE_URL'] = "postgresql://musiclive:npg_wopeP92YbXft@ep-curly-hat-ad4vut3o-pooler.c-2.us-east-1.aws.neon.tech/musiclive?sslmode=require&channel_binding=require"
        conn = get_connection()
        conn.close()
        
        # Check system resources
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check crawler status
        crawler_status_info = {
            "is_running": crawler_status.get("is_running", False),
            "current_progress": crawler_status.get("current_progress", {}),
            "last_activity": crawler_status.get("last_activity", "Never")
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "version": "1.0.0",
            "system": {
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "cpu_percent": psutil.cpu_percent(interval=1)
            },
            "crawler": crawler_status_info
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database": "disconnected",
            "error": str(e),
            "version": "1.0.0"
        }

@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics and performance data."""
    try:
        os.environ['DATABASE_URL'] = "postgresql://musiclive:npg_wopeP92YbXft@ep-curly-hat-ad4vut3o-pooler.c-2.us-east-1.aws.neon.tech/musiclive?sslmode=require&channel_binding=require"
        
        conn = get_connection()
        
        with conn.cursor() as cur:
            # Get event counts by date
            cur.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM event_instance
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """)
            daily_events = cur.fetchall()
            
            # Get venue counts
            cur.execute("SELECT COUNT(*) FROM venue")
            total_venues = cur.fetchone()[0]
            
            # Get source counts
            cur.execute("SELECT COUNT(*) FROM source")
            total_sources = cur.fetchone()[0]
            
            # Get artist counts
            cur.execute("SELECT COUNT(*) FROM artist")
            total_artists = cur.fetchone()[0]
            
            # Get recent crawl activity
            cur.execute("""
                SELECT COUNT(*) as count, 
                       AVG(EXTRACT(EPOCH FROM (finished_at - started_at))) as avg_duration
                FROM ingest_run
                WHERE started_at >= NOW() - INTERVAL '7 days'
                AND status = 'completed'
            """)
            recent_crawls = cur.fetchone()
            
        conn.close()
        
        # System metrics
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "cpu_percent": psutil.cpu_percent(interval=1)
            },
            "database": {
                "total_events": sum(row[1] for row in daily_events),
                "total_venues": total_venues,
                "total_sources": total_sources,
                "total_artists": total_artists,
                "daily_events": [{"date": str(row[0]), "count": row[1]} for row in daily_events]
            },
            "crawler": {
                "recent_crawls": recent_crawls[0] if recent_crawls[0] else 0,
                "avg_crawl_duration": recent_crawls[1] if recent_crawls[1] else 0,
                "current_status": crawler_status
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {"error": str(e)}

@app.get("/api/stats")
async def get_stats():
    """Get database statistics."""
    try:
        logger.info("Getting database stats...")
        
        # Set the database URL for the web interface
        os.environ['DATABASE_URL'] = "postgresql://musiclive:npg_wopeP92YbXft@ep-curly-hat-ad4vut3o-pooler.c-2.us-east-1.aws.neon.tech/musiclive?sslmode=require&channel_binding=require"
        logger.info("Database URL set")
        
        conn = get_connection()
        logger.info("Database connection established")
        
        with conn.cursor() as cur:
            # Count venues
            cur.execute("SELECT COUNT(*) FROM venue")
            total_venues = cur.fetchone()[0]
            logger.info(f"Venues count: {total_venues}")
            
            # Count events
            cur.execute("SELECT COUNT(*) FROM event_instance")
            total_events = cur.fetchone()[0]
            logger.info(f"Events count: {total_events}")
            
            # Count artists
            cur.execute("SELECT COUNT(*) FROM artist")
            total_artists = cur.fetchone()[0]
            logger.info(f"Artists count: {total_artists}")
            
            # Count sources
            cur.execute("SELECT COUNT(*) FROM source")
            total_sources = cur.fetchone()[0]
            logger.info(f"Sources count: {total_sources}")
        
        conn.close()
        logger.info("Database connection closed")
        
        result = {
            "total_venues": total_venues,
            "total_events": total_events,
            "total_artists": total_artists,
            "total_sources": total_sources
        }
        
        logger.info(f"Returning stats: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "total_venues": 0,
            "total_events": 0,
            "total_artists": 0,
            "total_sources": 0
        }

@app.get("/api/events")
async def get_events(
    venue_id: Optional[int] = None,
    artist_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get events with filtering and pagination."""
    try:
        os.environ['DATABASE_URL'] = "postgresql://musiclive:npg_wopeP92YbXft@ep-curly-hat-ad4vut3o-pooler.c-2.us-east-1.aws.neon.tech/musiclive?sslmode=require&channel_binding=require"
        
        conn = get_connection()
        
        # Build query with filters
        query = """
            SELECT e.id, e.title, e.artist_name, e.starts_at_utc, e.ends_at_utc, 
                   e.price_min, e.price_max, e.currency, e.ticket_url, e.age_restriction,
                   v.name as venue_name, v.city, v.state
            FROM event_instance e
            JOIN venue v ON e.venue_id = v.id
            WHERE 1=1
        """
        params = []
        
        if venue_id:
            query += " AND e.venue_id = %s"
            params.append(venue_id)
        
        if artist_name:
            query += " AND e.artist_name ILIKE %s"
            params.append(f"%{artist_name}%")
        
        if date_from:
            query += " AND e.starts_at_utc >= %s"
            params.append(date_from)
        
        if date_to:
            query += " AND e.starts_at_utc <= %s"
            params.append(date_to)
        
        # Add pagination
        query += " ORDER BY e.starts_at_utc ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        with conn.cursor() as cur:
            cur.execute(query, params)
            events = cur.fetchall()
            
            # Get total count for pagination
            count_query = query.replace("SELECT e.id, e.title", "SELECT COUNT(*)").split("ORDER BY")[0]
            cur.execute(count_query, params[:-2] if len(params) > 2 else params)
            total_count = cur.fetchone()[0]
        
        conn.close()
        
        return {
            "events": [
                {
                    "id": event[0],
                    "title": event[1],
                    "artist_name": event[2],
                    "starts_at_utc": event[3],
                    "ends_at_utc": event[4],
                    "price_min": event[5],
                    "price_max": event[6],
                    "currency": event[7],
                    "ticket_url": event[8],
                    "age_restriction": event[9],
                    "venue_name": event[10],
                    "city": event[11],
                    "state": event[12]
                } for event in events
            ],
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return {"events": [], "pagination": {"total": 0, "limit": limit, "offset": offset, "has_more": False}}

@app.get("/api/events/{event_id}")
async def get_event_detail(event_id: int):
    """Get detailed information about a specific event."""
    try:
        os.environ['DATABASE_URL'] = "postgresql://musiclive:npg_wopeP92YbXft@ep-curly-hat-ad4vut3o-pooler.c-2.us-east-1.aws.neon.tech/musiclive?sslmode=require&channel_binding=require"
        
        conn = get_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.id, e.title, e.artist_name, e.starts_at_utc, e.ends_at_utc, 
                       e.price_min, e.price_max, e.currency, e.ticket_url, e.age_restriction,
                       e.is_cancelled, e.created_at, e.updated_at,
                       v.name as venue_name, v.address_line1, v.city, v.state, v.postal_code,
                       v.latitude, v.longitude, v.tz_name
                FROM event_instance e
                JOIN venue v ON e.venue_id = v.id
                WHERE e.id = %s
            """, (event_id,))
            
            event = cur.fetchone()
            
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
        
        conn.close()
        
        return {
            "id": event[0],
            "title": event[1],
            "artist_name": event[2],
            "starts_at_utc": event[3],
            "ends_at_utc": event[4],
            "price_min": event[5],
            "price_max": event[6],
            "currency": event[7],
            "ticket_url": event[8],
            "age_restriction": event[9],
            "is_cancelled": event[10],
            "created_at": event[11],
            "updated_at": event[12],
            "venue": {
                "name": event[13],
                "address_line1": event[14],
                "city": event[15],
                "state": event[16],
                "postal_code": event[17],
                "latitude": event[18],
                "longitude": event[19],
                "tz_name": event[20]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/search")
async def search_events(
    q: str,
    limit: int = 20
):
    """Search events by title, artist, or venue name."""
    try:
        os.environ['DATABASE_URL'] = "postgresql://musiclive:npg_wopeP92YbXft@ep-curly-hat-ad4vut3o-pooler.c-2.us-east-1.aws.neon.tech/musiclive?sslmode=require&channel_binding=require"
        
        conn = get_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.id, e.title, e.artist_name, e.starts_at_utc, e.price_min, e.price_max,
                       v.name as venue_name, v.city, v.state
                FROM event_instance e
                JOIN venue v ON e.venue_id = v.id
                WHERE e.title ILIKE %s OR e.artist_name ILIKE %s OR v.name ILIKE %s
                ORDER BY e.starts_at_utc ASC
                LIMIT %s
            """, (f"%{q}%", f"%{q}%", f"%{q}%", limit))
            
            events = cur.fetchall()
        
        conn.close()
        
        return {
            "query": q,
            "results": [
                {
                    "id": event[0],
                    "title": event[1],
                    "artist_name": event[2],
                    "starts_at_utc": event[3],
                    "price_min": event[4],
                    "price_max": event[5],
                    "venue_name": event[6],
                    "city": event[7],
                    "state": event[8]
                } for event in events
            ],
            "total_results": len(events)
        }
        
    except Exception as e:
        logger.error(f"Error searching events: {e}")
        return {"query": q, "results": [], "total_results": 0}

@app.get("/api/crawl-history")
async def get_crawl_history():
    """Get crawl history and recent activity."""
    try:
        logger.info("Getting crawl history...")
        os.environ['DATABASE_URL'] = "postgresql://musiclive:npg_wopeP92YbXft@ep-curly-hat-ad4vut3o-pooler.c-2.us-east-1.aws.neon.tech/musiclive?sslmode=require&channel_binding=require"
        logger.info("Database URL set for crawl history")
        
        conn = get_connection()
        logger.info("Database connection established for crawl history")
        
        with conn.cursor() as cur:
            # Get recent events with venue names
            cur.execute("""
                SELECT v.name, e.title, e.starts_at_utc, e.created_at 
                FROM event_instance e
                JOIN venue v ON e.venue_id = v.id
                ORDER BY e.created_at DESC 
                LIMIT 10
            """)
            recent_events = cur.fetchall()
            
            # Get recent venues
            cur.execute("""
                SELECT name, created_at 
                FROM venue 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent_venues = cur.fetchall()
            
            # Get recent sources
            cur.execute("""
                SELECT url, name, created_at 
                FROM source 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent_sources = cur.fetchall()
        
        conn.close()
        
        return {
            "recent_events": [
                {
                    "venue": event[0],
                    "title": event[1],
                    "starts_at": event[2],
                    "discovered_at": event[3]
                } for event in recent_events
            ],
            "recent_venues": [
                {
                    "name": venue[0],
                    "discovered_at": venue[1]
                } for venue in recent_venues
            ],
            "recent_sources": [
                {
                    "url": source[0],
                    "name": source[1],
                    "discovered_at": source[2]
                } for source in recent_sources
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting crawl history: {e}")
        return {
            "recent_events": [],
            "recent_venues": [],
            "recent_sources": []
        }

async def run_crawl_background(site_slug: str, city: str, state: str, max_sources: int):
    """Run crawl in background task."""
    try:
        logger.info(f"Starting background crawl for {city}, {state}")
        
        # Run the crawl
        result = await discover_and_crawl_sources(site_slug, city, state, max_sources)
        
        # Update status
        crawler_status['is_running'] = False
        crawler_status['last_run'] = datetime.now().isoformat()
        crawler_status['successful_runs'] += 1
        
        logger.info(f"Background crawl completed successfully")
        
    except Exception as e:
        logger.error(f"Background crawl failed: {e}")
        crawler_status['is_running'] = False
        crawler_status['failed_runs'] += 1

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
