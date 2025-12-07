"""
Bitwarden Session Manager for sharing BW_SESSION across all agents
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BitwardenSessionManager:
    """Manages Bitwarden session sharing across all agents."""
    
    def __init__(self):
        self.session_file = ".bw_session"
        self.session_export_file = ".bw_session_export.sh"
    
    def get_session_from_env(self) -> Optional[str]:
        """Get BW_SESSION from environment variables."""
        return os.getenv('BW_SESSION')
    
    def get_session_from_file(self) -> Optional[str]:
        """Get BW_SESSION from session file."""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"Failed to read session file: {e}")
        return None
    
    def save_session_to_file(self, session_token: str):
        """Save BW_SESSION to file for sharing."""
        try:
            with open(self.session_file, 'w') as f:
                f.write(session_token)
            logger.info("✅ BW_SESSION saved to file for agent sharing")
        except Exception as e:
            logger.error(f"Failed to save session to file: {e}")
    
    def ensure_session_available(self) -> bool:
        """Ensure BW_SESSION is available to all agents."""
        session_token = self.get_session_from_env() or self.get_session_from_file()
        
        if not session_token:
            logger.warning("❌ No BW_SESSION found in environment or file")
            return False
        
        # Set environment variable for current process and subprocesses
        os.environ['BW_SESSION'] = session_token
        
        # Save to file for other processes
        self.save_session_to_file(session_token)
        
        logger.info("✅ BW_SESSION is available to all agents")
        return True
    
    def check_session_validity(self) -> bool:
        """Check if the current BW_SESSION is valid."""
        try:
            import subprocess
            result = subprocess.run(
                ['./bw', 'status'],
                capture_output=True,
                text=True,
                env=os.environ
            )
            
            if result.returncode == 0:
                import json
                status = json.loads(result.stdout)
                if status.get('status') == 'unlocked':
                    logger.info("✅ BW_SESSION is valid and vault is unlocked")
                    return True
                else:
                    logger.warning(f"⚠️ BW_SESSION exists but vault status: {status.get('status')}")
                    return False
            else:
                logger.error(f"❌ BW_SESSION validation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to validate BW_SESSION: {e}")
            return False
    
    def initialize_for_agents(self) -> bool:
        """Initialize Bitwarden session for all agents."""
        if not self.ensure_session_available():
            logger.error("❌ Cannot initialize Bitwarden session - no session available")
            return False
        
        if not self.check_session_validity():
            logger.error("❌ Cannot initialize Bitwarden session - session is invalid")
            return False
        
        logger.info("✅ Bitwarden session initialized successfully for all agents")
        return True


# Global session manager instance
session_manager = BitwardenSessionManager()


def initialize_bitwarden_session() -> bool:
    """Initialize Bitwarden session for the current process."""
    try:
        return session_manager.initialize_for_agents()
    except Exception as e:
        logger.error(f"Failed to initialize Bitwarden session: {e}")
        return False


def get_bitwarden_session() -> Optional[str]:
    """Get the current Bitwarden session token."""
    return session_manager.get_session_from_env()


def is_bitwarden_authenticated() -> bool:
    """Check if Bitwarden is properly authenticated."""
    try:
        return session_manager.check_session_validity()
    except Exception as e:
        logger.error(f"Failed to check Bitwarden authentication: {e}")
        return False


# Auto-initialize when module is imported (don't raise on failure)
initialize_bitwarden_session()
