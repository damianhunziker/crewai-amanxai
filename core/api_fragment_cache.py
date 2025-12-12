"""
API Fragment Cache System for Lazy Loading OpenAPI Specifications

This module implements a fragment-based caching system for OpenAPI specifications
where LLMs only load relevant parts of API specs on demand.
"""

import json
import logging
import sqlite3
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pickle
import re

from .settings import settings

logger = logging.getLogger(__name__)


@dataclass
class APIFragment:
    """Represents a fragment of an OpenAPI specification."""
    fragment_id: str
    api_id: str
    fragment_type: str  # 'endpoint', 'schema', 'parameter', 'security'
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    usage_count: int = 0
    last_used: Optional[datetime] = None
    embedding: Optional[List[float]] = None  # For semantic search
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert fragment to dictionary."""
        data = asdict(self)
        data['created_at'] = data['created_at'].isoformat()
        data['updated_at'] = data['updated_at'].isoformat()
        if data['last_used']:
            data['last_used'] = data['last_used'].isoformat()
        return data


@dataclass
class FragmentQuery:
    """Query for finding relevant fragments."""
    api_id: Optional[str] = None
    intent: Optional[str] = None
    fragment_types: Optional[List[str]] = None
    min_confidence: float = 0.7
    limit: int = 10


class APIFragmentCache:
    """Manages caching and retrieval of API fragments."""
    
    def __init__(self, db_path: str = "api_fragments.db"):
        """Initialize the fragment cache."""
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for fragment storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Fragments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fragments (
                fragment_id TEXT PRIMARY KEY,
                api_id TEXT NOT NULL,
                fragment_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                embedding BLOB
            )
        """)
        
        # Create indexes separately
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fragments_api_id ON fragments (api_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fragments_fragment_type ON fragments (fragment_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fragments_usage_count ON fragments (usage_count)")
        
        # Fragment relationships (for dependency tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fragment_relationships (
                parent_fragment_id TEXT,
                child_fragment_id TEXT,
                relationship_type TEXT,
                PRIMARY KEY (parent_fragment_id, child_fragment_id),
                FOREIGN KEY (parent_fragment_id) REFERENCES fragments (fragment_id),
                FOREIGN KEY (child_fragment_id) REFERENCES fragments (fragment_id)
            )
        """)
        
        # API metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_metadata (
                api_id TEXT PRIMARY KEY,
                full_spec_url TEXT,
                last_fetched TIMESTAMP,
                etag TEXT,
                version TEXT,
                fragment_count INTEGER DEFAULT 0,
                total_usage INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Fragment cache database initialized at {self.db_path}")
    
    def store_fragment(self, fragment: APIFragment) -> bool:
        """Store a fragment in the cache."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if fragment exists
            cursor.execute(
                "SELECT fragment_id FROM fragments WHERE fragment_id = ?",
                (fragment.fragment_id,)
            )
            
            if cursor.fetchone():
                # Update existing fragment
                cursor.execute("""
                    UPDATE fragments SET
                        content = ?,
                        metadata = ?,
                        updated_at = ?,
                        embedding = ?
                    WHERE fragment_id = ?
                """, (
                    json.dumps(fragment.content),
                    json.dumps(fragment.metadata),
                    fragment.updated_at.isoformat(),
                    pickle.dumps(fragment.embedding) if fragment.embedding else None,
                    fragment.fragment_id
                ))
            else:
                # Insert new fragment
                cursor.execute("""
                    INSERT INTO fragments (
                        fragment_id, api_id, fragment_type, content,
                        metadata, created_at, updated_at, usage_count,
                        last_used, embedding
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fragment.fragment_id,
                    fragment.api_id,
                    fragment.fragment_type,
                    json.dumps(fragment.content),
                    json.dumps(fragment.metadata),
                    fragment.created_at.isoformat(),
                    fragment.updated_at.isoformat(),
                    fragment.usage_count,
                    fragment.last_used.isoformat() if fragment.last_used else None,
                    pickle.dumps(fragment.embedding) if fragment.embedding else None
                ))
            
            conn.commit()
            conn.close()
            logger.debug(f"✅ Fragment stored: {fragment.fragment_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing fragment {fragment.fragment_id}: {e}")
            return False
    
    def get_fragment(self, fragment_id: str) -> Optional[APIFragment]:
        """Retrieve a fragment by ID."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM fragments WHERE fragment_id = ?
            """, (fragment_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Update usage stats
            self._increment_usage(fragment_id)
            
            return self._row_to_fragment(row)
            
        except Exception as e:
            logger.error(f"❌ Error retrieving fragment {fragment_id}: {e}")
            return None
    
    def find_fragments(self, query: FragmentQuery) -> List[APIFragment]:
        """Find fragments matching the query."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query
            sql = "SELECT * FROM fragments WHERE 1=1"
            params = []
            
            if query.api_id:
                sql += " AND api_id = ?"
                params.append(query.api_id)
            
            if query.fragment_types:
                placeholders = ','.join(['?'] * len(query.fragment_types))
                sql += f" AND fragment_type IN ({placeholders})"
                params.extend(query.fragment_types)
            
            # Order by usage count (most used first)
            sql += " ORDER BY usage_count DESC, updated_at DESC"
            sql += " LIMIT ?"
            params.append(query.limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            
            fragments = [self._row_to_fragment(row) for row in rows]
            
            # Update usage for retrieved fragments
            for fragment in fragments:
                self._increment_usage(fragment.fragment_id)
            
            logger.debug(f"✅ Found {len(fragments)} fragments for query")
            return fragments
            
        except Exception as e:
            logger.error(f"❌ Error finding fragments: {e}")
            return []
    
    def find_fragments_by_intent(self, api_id: str, intent: str) -> List[APIFragment]:
        """
        Find fragments relevant to a specific intent using semantic search.
        This is a simplified version - in production would use vector embeddings.
        """
        # For now, use keyword matching
        keywords = self._extract_keywords(intent)
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Search in metadata (simplified semantic search)
            fragments = []
            for keyword in keywords:
                cursor.execute("""
                    SELECT * FROM fragments 
                    WHERE api_id = ? 
                    AND (metadata LIKE ? OR fragment_type LIKE ?)
                    ORDER BY usage_count DESC
                    LIMIT 5
                """, (api_id, f'%{keyword}%', f'%{keyword}%'))
                
                for row in cursor.fetchall():
                    fragment = self._row_to_fragment(row)
                    if fragment not in fragments:
                        fragments.append(fragment)
            
            conn.close()
            
            # Update usage
            for fragment in fragments:
                self._increment_usage(fragment.fragment_id)
            
            return fragments[:10]  # Limit results
            
        except Exception as e:
            logger.error(f"❌ Error finding fragments by intent: {e}")
            return []
    
    def extract_fragments_from_spec(self, api_id: str, openapi_spec: Dict[str, Any]) -> List[APIFragment]:
        """Extract fragments from a full OpenAPI specification."""
        fragments = []
        
        # Extract endpoints
        for path, methods in openapi_spec.get('paths', {}).items():
            for method, details in methods.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    fragment_id = self._generate_fragment_id(api_id, 'endpoint', f"{method}:{path}")
                    
                    fragment = APIFragment(
                        fragment_id=fragment_id,
                        api_id=api_id,
                        fragment_type='endpoint',
                        content={
                            'path': path,
                            'method': method.upper(),
                            'operation': details
                        },
                        metadata={
                            'summary': details.get('summary', ''),
                            'description': details.get('description', ''),
                            'operation_id': details.get('operationId', ''),
                            'tags': details.get('tags', []),
                            'keywords': self._extract_keywords_from_text(
                                f"{details.get('summary', '')} {details.get('description', '')}"
                            )
                        },
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    fragments.append(fragment)
        
        # Extract schemas
        for schema_name, schema_def in openapi_spec.get('components', {}).get('schemas', {}).items():
            fragment_id = self._generate_fragment_id(api_id, 'schema', schema_name)
            
            fragment = APIFragment(
                fragment_id=fragment_id,
                api_id=api_id,
                fragment_type='schema',
                content={
                    'name': schema_name,
                    'schema': schema_def
                },
                metadata={
                    'description': schema_def.get('description', ''),
                    'type': schema_def.get('type', 'object'),
                    'keywords': self._extract_keywords_from_text(schema_def.get('description', ''))
                },
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            fragments.append(fragment)
        
        logger.info(f"✅ Extracted {len(fragments)} fragments from {api_id} spec")
        return fragments
    
    def _generate_fragment_id(self, api_id: str, fragment_type: str, identifier: str) -> str:
        """Generate a unique fragment ID."""
        content = f"{api_id}:{fragment_type}:{identifier}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for semantic search."""
        if not text:
            return []
        
        # Remove special characters and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return list(set(keywords))[:10]  # Return unique keywords, max 10
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract keywords from text for metadata."""
        return self._extract_keywords(text)
    
    def _row_to_fragment(self, row) -> APIFragment:
        """Convert SQLite row to APIFragment object."""
        return APIFragment(
            fragment_id=row['fragment_id'],
            api_id=row['api_id'],
            fragment_type=row['fragment_type'],
            content=json.loads(row['content']),
            metadata=json.loads(row['metadata']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            usage_count=row['usage_count'],
            last_used=datetime.fromisoformat(row['last_used']) if row['last_used'] else None,
            embedding=pickle.loads(row['embedding']) if row['embedding'] else None
        )
    
    def _increment_usage(self, fragment_id: str):
        """Increment usage count for a fragment."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE fragments 
                SET usage_count = usage_count + 1, 
                    last_used = ?
                WHERE fragment_id = ?
            """, (datetime.now().isoformat(), fragment_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error incrementing usage for {fragment_id}: {e}")
    
    def cleanup_old_fragments(self, days_old: int = 30):
        """Remove fragments that haven't been used in specified days."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Handle NULL last_used values (treat as very old)
            cursor.execute("""
                DELETE FROM fragments 
                WHERE (last_used IS NULL OR last_used < ?) AND usage_count = 0
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Cleaned up {deleted_count} old fragments")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old fragments: {e}")
            return 0
    
    def get_api_stats(self, api_id: str) -> Dict[str, Any]:
        """Get statistics for an API."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dictionary-like access
            cursor = conn.cursor()
            
            # Get fragment count
            cursor.execute("""
                SELECT COUNT(*) as count, fragment_type 
                FROM fragments 
                WHERE api_id = ? 
                GROUP BY fragment_type
            """, (api_id,))
            
            fragment_stats = {}
            total_fragments = 0
            for row in cursor.fetchall():
                fragment_type = row['fragment_type']
                count = row['count']
                fragment_stats[fragment_type] = count
                total_fragments += count
            
            # Get usage stats
            cursor.execute("""
                SELECT SUM(usage_count) as total_usage,
                       AVG(usage_count) as avg_usage,
                       MAX(last_used) as last_used
                FROM fragments 
                WHERE api_id = ?
            """, (api_id,))
            
            usage_row = cursor.fetchone()
            
            conn.close()
            
            # Handle None values from SQL aggregation
            total_usage = usage_row['total_usage'] if usage_row and usage_row['total_usage'] is not None else 0
            avg_usage = usage_row['avg_usage'] if usage_row and usage_row['avg_usage'] is not None else 0.0
            last_used = usage_row['last_used'] if usage_row else None
            
            return {
                'api_id': api_id,
                'total_fragments': total_fragments,
                'fragment_stats': fragment_stats,
                'total_usage': total_usage,
                'average_usage': float(avg_usage),
                'last_used': last_used
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting API stats for {api_id}: {e}")
            return {}


# Singleton instance for easy access
fragment_cache = APIFragmentCache()
