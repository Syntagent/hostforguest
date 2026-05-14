-- Create user_sessions table for database-based token storage
-- This replaces JWT token storage with secure database sessions

CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id UUID NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    user_agent VARCHAR(500),
    ip_address VARCHAR(45), -- IPv6 support
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMP NOT NULL,
    refresh_expires_at TIMESTAMP,
    last_activity TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh_token ON user_sessions(refresh_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_host_id ON user_sessions(host_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_is_active ON user_sessions(is_active);

-- Add comment
COMMENT ON TABLE user_sessions IS 'Database-based session storage for secure token management';
COMMENT ON COLUMN user_sessions.session_token IS 'Secure random session token for authentication';
COMMENT ON COLUMN user_sessions.refresh_token IS 'Secure random refresh token for session renewal';
COMMENT ON COLUMN user_sessions.is_active IS 'Whether the session is currently active';
COMMENT ON COLUMN user_sessions.expires_at IS 'When the session token expires';
COMMENT ON COLUMN user_sessions.refresh_expires_at IS 'When the refresh token expires';
