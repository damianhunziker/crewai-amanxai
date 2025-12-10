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
            logger.warning("⚠️ No BW_SESSION found in environment or file")
            return False  # Session is required for proper function

        # Set environment variable for current process and ALL subprocesses
        os.environ['BW_SESSION'] = session_token

        # Save to file for persistence across restarts
        self.save_session_to_file(session_token)

        # Export to shell for subprocess inheritance
        self._export_session_to_shell()

        # Verify session is working
        if self._verify_session_works():
            logger.info("✅ BW_SESSION is available and working for all agents")
            return True
        else:
            logger.error("❌ BW_SESSION exists but doesn't work")
            return False

    def _export_session_to_shell(self):
        """Export BW_SESSION to shell environment for all subprocesses."""
        try:
            # Create export script for shell inheritance
            export_script = f"""#!/bin/bash
export BW_SESSION="{os.environ.get('BW_SESSION', '')}"
"""
            with open(self.session_export_file, 'w') as f:
                f.write(export_script)
            os.chmod(self.session_export_file, 0o755)

            logger.debug("✅ BW_SESSION export script created")
        except Exception as e:
            logger.warning(f"⚠️ Could not create export script: {e}")

    def _verify_session_works(self) -> bool:
        """Verify that the BW_SESSION actually works."""
        try:
            import subprocess

            # Use the session to run a simple command
            env = os.environ.copy()
            env['BW_SESSION'] = os.environ.get('BW_SESSION', '')

            result = subprocess.run(
                ['bw', 'status', '--raw'],
                capture_output=True,
                text=True,
                env=env,
                timeout=10
            )

            if result.returncode == 0 and 'unlocked' in result.stdout.lower():
                return True
            else:
                logger.warning(f"⚠️ BW_SESSION verification failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ BW_SESSION verification error: {e}")
            return False
    
    def check_session_validity(self) -> bool:
        """Check if the current BW_SESSION is valid and unlock if needed."""
        try:
            import subprocess
            result = subprocess.run(
                ['bw', 'status'],
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
                    # Try to unlock with existing session
                    return self._try_unlock_with_session()
            else:
                logger.error(f"❌ BW_SESSION validation failed: {result.stderr}")
                return False

        except FileNotFoundError:
            logger.warning("⚠️ Bitwarden CLI (bw) not installed - skipping session validation")
            return False  # Don't fail if bw is not installed
        except Exception as e:
            logger.error(f"❌ Failed to validate BW_SESSION: {e}")
            return False

    def _try_unlock_with_session(self) -> bool:
        """Try to unlock vault with existing session."""
        try:
            # If we have a session, try to unlock
            session_token = self.get_session_from_env() or self.get_session_from_file()
            if session_token:
                # Set session and try unlock command
                env = os.environ.copy()
                env['BW_SESSION'] = session_token

                import subprocess
                result = subprocess.run(
                    ['bw', 'unlock', '--check'],
                    capture_output=True,
                    text=True,
                    env=env
                )

                if result.returncode == 0:
                    logger.info("✅ Vault unlocked with existing session")
                    return True
                else:
                    logger.warning("⚠️ Could not unlock vault with existing session")
                    return False
            else:
                logger.warning("⚠️ No session available to unlock vault")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to unlock vault: {e}")
            return False
    
    def initialize_for_agents(self) -> bool:
        """Initialize Bitwarden session for all agents with auto-login fallback."""
        # First try to use existing session
        if self.ensure_session_available() and self.check_session_validity():
            logger.info("✅ Existing Bitwarden session is valid")
            return True

        # If no valid session, try auto-login
        logger.info("🔄 No valid session found, attempting auto-login...")
        if self._perform_auto_login():
            logger.info("✅ Auto-login successful, session initialized")
            return True

        logger.error("❌ Cannot initialize Bitwarden session - auto-login failed")
        return False

    def _perform_auto_login(self) -> bool:
        """Perform automatic login using environment credentials."""
        from .bitwarden_cli_integration import BitwardenCLIIntegration

        try:
            client = BitwardenCLIIntegration()

            # Check if already logged in
            if client.is_logged_in():
                status = client.get_status()
                if status.get('status') == 'unlocked':
                    logger.info("✅ Already logged in and unlocked")
                    # Ensure session is saved
                    session_token = os.getenv('BW_SESSION') or client.session_key
                    if session_token:
                        self.save_session_to_file(session_token)
                        os.environ['BW_SESSION'] = session_token
                    return True

            # Try login with 2FA if needed
            if client.login_with_2fa():
                logger.info("✅ Auto-login with 2FA successful")
                # Save session for future use
                if client.session_key:
                    self.save_session_to_file(client.session_key)
                    os.environ['BW_SESSION'] = client.session_key
                return True
            elif client.login():
                logger.info("✅ Auto-login successful")
                # Save session for future use
                if client.session_key:
                    self.save_session_to_file(client.session_key)
                    os.environ['BW_SESSION'] = client.session_key
                return True
            else:
                logger.error("❌ Auto-login failed - check BITWARDEN_AGENT_EMAIL and BITWARDEN_AGENT_PASSWORD")
                return False

        except Exception as e:
            logger.error(f"❌ Auto-login error: {e}")
            return False


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
