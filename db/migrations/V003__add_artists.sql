-- V003__add_artists.sql
-- Add artists dimension and related tables

-- Artists table
CREATE TABLE IF NOT EXISTS artist (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES site(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    bio TEXT,
    genre_tags TEXT[], -- Array of genre tags
    hometown VARCHAR(255),
    active_years VARCHAR(100),
    official_website VARCHAR(500),
    social_media JSONB, -- Store social media links as JSON
    primary_photo_url VARCHAR(500),
    primary_photo_data BYTEA, -- Store actual image data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(site_id, name)
);

-- Artist-event relationships
CREATE TABLE IF NOT EXISTS artist_event_link (
    id SERIAL PRIMARY KEY,
    artist_id INTEGER NOT NULL REFERENCES artist(id) ON DELETE CASCADE,
    event_instance_id INTEGER NOT NULL REFERENCES event_instance(id) ON DELETE CASCADE,
    role VARCHAR(100) DEFAULT 'performer', -- performer, opener, special_guest, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(artist_id, event_instance_id)
);

-- Artist discovery tracking
CREATE TABLE IF NOT EXISTS artist_discovery (
    id SERIAL PRIMARY KEY,
    artist_id INTEGER NOT NULL REFERENCES artist(id) ON DELETE CASCADE,
    source_url VARCHAR(500) NOT NULL,
    discovery_method VARCHAR(100), -- 'event_extraction', 'manual_research', 'api_lookup'
    confidence_score DECIMAL(3,2) DEFAULT 0.0,
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_researched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    research_status VARCHAR(50) DEFAULT 'pending' -- pending, in_progress, completed, failed
);

-- Artist research queue
CREATE TABLE IF NOT EXISTS artist_research_queue (
    id SERIAL PRIMARY KEY,
    artist_id INTEGER NOT NULL REFERENCES artist(id) ON DELETE CASCADE,
    priority INTEGER DEFAULT 1, -- Higher number = higher priority
    research_type VARCHAR(100), -- 'basic_info', 'social_media', 'photos', 'discography'
    queued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'queued' -- queued, in_progress, completed, failed
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_artist_site_id ON artist(site_id);
CREATE INDEX IF NOT EXISTS idx_artist_name ON artist(name);
CREATE INDEX IF NOT EXISTS idx_artist_event_link_artist_id ON artist_event_link(artist_id);
CREATE INDEX IF NOT EXISTS idx_artist_event_link_event_id ON artist_event_link(event_instance_id);
CREATE INDEX IF NOT EXISTS idx_artist_discovery_artist_id ON artist_discovery(artist_id);
CREATE INDEX IF NOT EXISTS idx_artist_research_queue_priority ON artist_research_queue(priority DESC);
CREATE INDEX IF NOT EXISTS idx_artist_research_queue_status ON artist_research_queue(status);

-- Add artist_id to event_instance for direct linking
ALTER TABLE event_instance ADD COLUMN IF NOT EXISTS artist_id INTEGER REFERENCES artist(id) ON DELETE SET NULL;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_artist_updated_at BEFORE UPDATE ON artist FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
