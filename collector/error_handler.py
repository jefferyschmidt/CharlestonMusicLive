"""
Error Handling and Recovery System

Handles various types of errors during crawling and provides recovery strategies.
"""
import logging
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CrawlError:
    """Represents a crawl error with context."""
    error_type: str
    message: str
    source_url: str
    timestamp: datetime
    retry_count: int = 0
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class ErrorHandler:
    """Handles errors and provides recovery strategies."""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.recovery_strategies: Dict[str, Callable] = {}
        self.blacklisted_sources: set = set()
        
        # Register recovery strategies
        self._register_recovery_strategies()
    
    def _register_recovery_strategies(self):
        """Register recovery strategies for different error types."""
        self.recovery_strategies = {
            'http_429': self._handle_rate_limit,
            'http_403': self._handle_forbidden,
            'http_500': self._handle_server_error,
            'timeout': self._handle_timeout,
            'connection_error': self._handle_connection_error,
            'parsing_error': self._handle_parsing_error,
            'extraction_error': self._handle_extraction_error
        }
    
    def handle_error(self, error: CrawlError) -> Dict[str, Any]:
        """Handle an error and return recovery action."""
        try:
            # Update error counts
            error_key = f"{error.source_url}:{error.error_type}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            # Check if source should be blacklisted
            if self._should_blacklist(error):
                self.blacklisted_sources.add(error.source_url)
                logger.warning(f"Blacklisted source due to repeated errors: {error.source_url}")
                return {
                    'action': 'blacklist',
                    'delay': 0,
                    'retry': False,
                    'message': f"Source blacklisted due to repeated {error.error_type} errors"
                }
            
            # Get recovery strategy
            if error.error_type in self.recovery_strategies:
                return self.recovery_strategies[error.error_type](error)
            else:
                return self._handle_unknown_error(error)
                
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            return {
                'action': 'skip',
                'delay': 5,
                'retry': False,
                'message': f"Error handler failed: {e}"
            }
    
    def _should_blacklist(self, error: CrawlError) -> bool:
        """Determine if a source should be blacklisted."""
        error_key = f"{error.source_url}:{error.error_type}"
        error_count = self.error_counts.get(error_key, 0)
        
        # Blacklist after 5 errors of the same type
        if error_count >= 5:
            return True
        
        # Blacklist after 10 total errors from the same source
        source_errors = sum(1 for k, v in self.error_counts.items() 
                          if k.startswith(f"{error.source_url}:") and v > 0)
        if source_errors >= 10:
            return True
        
        return False
    
    def _handle_rate_limit(self, error: CrawlError) -> Dict[str, Any]:
        """Handle rate limiting errors."""
        delay = min(60 * (2 ** error.retry_count), 3600)  # Exponential backoff, max 1 hour
        
        return {
            'action': 'retry',
            'delay': delay,
            'retry': True,
            'message': f"Rate limited, waiting {delay} seconds"
        }
    
    def _handle_forbidden(self, error: CrawlError) -> Dict[str, Any]:
        """Handle forbidden/403 errors."""
        if error.retry_count >= 2:
            return {
                'action': 'skip',
                'delay': 0,
                'retry': False,
                'message': "Access forbidden, skipping source"
            }
        
        return {
            'action': 'retry',
            'delay': 30,
            'retry': True,
            'message': "Access forbidden, retrying with delay"
        }
    
    def _handle_server_error(self, error: CrawlError) -> Dict[str, Any]:
        """Handle server errors."""
        delay = min(30 * (2 ** error.retry_count), 300)  # Exponential backoff, max 5 minutes
        
        if error.retry_count >= 3:
            return {
                'action': 'skip',
                'delay': 0,
                'retry': False,
                'message': "Server errors persist, skipping source"
            }
        
        return {
            'action': 'retry',
            'delay': delay,
            'retry': True,
            'message': f"Server error, retrying in {delay} seconds"
        }
    
    def _handle_timeout(self, error: CrawlError) -> Dict[str, Any]:
        """Handle timeout errors."""
        delay = min(10 * (2 ** error.retry_count), 60)
        
        if error.retry_count >= 2:
            return {
                'action': 'skip',
                'delay': 0,
                'retry': False,
                'message': "Timeout errors persist, skipping source"
            }
        
        return {
            'action': 'retry',
            'delay': delay,
            'retry': True,
            'message': f"Timeout, retrying in {delay} seconds"
        }
    
    def _handle_connection_error(self, error: CrawlError) -> Dict[str, Any]:
        """Handle connection errors."""
        delay = min(15 * (2 ** error.retry_count), 120)
        
        if error.retry_count >= 3:
            return {
                'action': 'skip',
                'delay': 0,
                'retry': False,
                'message': "Connection errors persist, skipping source"
            }
        
        return {
            'action': 'retry',
            'delay': delay,
            'retry': True,
            'message': f"Connection error, retrying in {delay} seconds"
        }
    
    def _handle_parsing_error(self, error: CrawlError) -> Dict[str, Any]:
        """Handle HTML parsing errors."""
        return {
            'action': 'skip',
            'delay': 0,
            'retry': False,
            'message': "HTML parsing failed, skipping source"
        }
    
    def _handle_extraction_error(self, error: CrawlError) -> Dict[str, Any]:
        """Handle event extraction errors."""
        return {
            'action': 'skip',
            'delay': 0,
            'retry': False,
            'message': "Event extraction failed, skipping source"
        }
    
    def _handle_unknown_error(self, error: CrawlError) -> Dict[str, Any]:
        """Handle unknown error types."""
        return {
            'action': 'skip',
            'delay': 10,
            'retry': False,
            'message': f"Unknown error: {error.error_type}"
        }
    
    def is_source_blacklisted(self, source_url: str) -> bool:
        """Check if a source is blacklisted."""
        return source_url in self.blacklisted_sources
    
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of current errors."""
        return {
            'total_errors': sum(self.error_counts.values()),
            'blacklisted_sources': len(self.blacklisted_sources),
            'error_types': list(set(k.split(':')[1] for k in self.error_counts.keys())),
            'top_error_sources': sorted(
                [(k.split(':')[0], v) for k, v in self.error_counts.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    
    def reset_errors(self, source_url: str = None):
        """Reset error counts for a source or all sources."""
        if source_url:
            # Reset errors for specific source
            keys_to_remove = [k for k in self.error_counts.keys() if k.startswith(f"{source_url}:")]
            for key in keys_to_remove:
                del self.error_counts[key]
            self.blacklisted_sources.discard(source_url)
        else:
            # Reset all errors
            self.error_counts.clear()
            self.blacklisted_sources.clear()
