"""
Bitwarden CLI Integration for CrewAI Agents

Provides secure API key management through Bitwarden CLI (bw command).
Agents can securely retrieve API keys from Bitwarden collections using the official CLI.
"""

import os
import json
import logging
import subprocess
import tempfile
import shutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import getpass

logger = logging.getLogger(__name__)


class BitwardenCLIError(Exception):
    """Custom exception for Bitwarden CLI operations"""
    pass


class BitwardenCLIIntegration:
    """Bitwarden CLI Integration using subprocess"""
    
    def __init__(self, bw_path: str = "bw"):
        self.bw_path = bw_path
        self.session_key = os.getenv('BW_SESSION')  # Initialize from env if available
        self._check_bw_installation()

        # Environment variables for Bitwarden credentials
        self.email = os.getenv('BITWARDEN_AGENT_EMAIL')
        self.password = os.getenv('BITWARDEN_AGENT_PASSWORD')

        if not self.email or not self.password:
            logger.warning("⚠️ Bitwarden credentials not found in environment variables")
    
    def _check_bw_installation(self) -> None:
        """Check if Bitwarden CLI is installed and accessible"""
        try:
            result = subprocess.run(
                [self.bw_path, "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"✅ Bitwarden CLI found: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise BitwardenCLIError(
                "Bitwarden CLI not found. Please install it from: "
                "https://bitwarden.com/help/cli/"
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get Bitwarden CLI status

        Returns:
            Status information
        """
        try:
            stdout, stderr = self._run_bw_command(["status"])
            if stdout:
                return json.loads(stdout)
            return {}
        except (BitwardenCLIError, json.JSONDecodeError):
            return {}

    def _run_bw_command(self, command: List[str], capture_output: bool = True, force_session: bool = True) -> Tuple[str, str]:
        """
        Run Bitwarden CLI command with proper session handling

        Args:
            command: List of command arguments
            capture_output: Whether to capture stdout/stderr
            force_session: Whether to ensure session is available

        Returns:
            Tuple of (stdout, stderr)
        """
        try:
            # Ensure session is available if required
            if force_session and not self._ensure_session_for_command():
                raise BitwardenCLIError("No valid Bitwarden session available")

            env = os.environ.copy()

            # Always set BW_SESSION from environment/file if available
            session_token = os.getenv('BW_SESSION')
            if not session_token:
                # Try to load from session file
                try:
                    with open('.bw_session', 'r') as f:
                        session_token = f.read().strip()
                except:
                    pass

            if session_token:
                env['BW_SESSION'] = session_token
                logger.debug(f"Using BW_SESSION: {session_token[:20]}...")
            else:
                logger.warning("No BW_SESSION available for command")

            full_command = [self.bw_path] + command
            logger.debug(f"Running CLI command: {' '.join(full_command)}")

            result = subprocess.run(
                full_command,
                capture_output=capture_output,
                text=True,
                env=env,
                input='',  # Prevent interactive password prompts
                check=True
            )

            logger.debug(f"CLI stdout: {result.stdout.strip()}")
            logger.debug(f"CLI stderr: {result.stderr.strip()}")

            return result.stdout.strip(), result.stderr.strip()

        except subprocess.CalledProcessError as e:
            # Check if it's an authentication error
            if "Master password" in str(e.stderr) or "BW_SESSION" in str(e.stderr):
                logger.warning("Session expired, attempting to refresh...")
                if self._refresh_session():
                    # Retry command once with refreshed session
                    return self._run_bw_command(command, capture_output, force_session=False)
                else:
                    raise BitwardenCLIError("Session refresh failed")
            else:
                logger.error(f"❌ Bitwarden CLI command failed: {e}")
                logger.error(f"Command: bw {' '.join(command)}")
                logger.error(f"Stderr: {e.stderr}")
                logger.error(f"Stdout: {e.stdout}")
                raise BitwardenCLIError(f"Bitwarden CLI error: {e.stderr}")
        except Exception as e:
            logger.error(f"❌ Unexpected error running Bitwarden CLI: {e}")
            raise BitwardenCLIError(f"Unexpected error: {e}")

    def _ensure_session_for_command(self) -> bool:
        """Ensure a valid session is available for commands"""
        # First check if we already have a valid session
        if self._is_session_valid():
            return True

        # Try to load session from file/environment
        session_token = os.getenv('BW_SESSION')
        if not session_token:
            try:
                with open('.bw_session', 'r') as f:
                    session_token = f.read().strip()
            except:
                pass

        if session_token:
            os.environ['BW_SESSION'] = session_token
            self.session_key = session_token
            if self._is_session_valid():
                logger.info("✅ Loaded valid session from storage")
                return True

        # Last resort: try to unlock vault
        logger.info("🔄 Attempting to unlock vault for new session...")
        if self.unlock():
            return True

        logger.error("❌ No valid session available")
        return False

    def _is_session_valid(self) -> bool:
        """Check if current session is valid"""
        try:
            # Quick status check
            result = subprocess.run(
                [self.bw_path, 'status', '--raw'],
                capture_output=True,
                text=True,
                env=os.environ,
                timeout=5
            )
            return result.returncode == 0 and 'unlocked' in result.stdout.lower()
        except:
            return False

    def _refresh_session(self) -> bool:
        """Refresh the current session"""
        try:
            logger.info("🔄 Refreshing Bitwarden session...")

            # Clear current session
            self.session_key = None
            if 'BW_SESSION' in os.environ:
                del os.environ['BW_SESSION']

            # Try to unlock with stored credentials
            if self.unlock():
                logger.info("✅ Session refreshed successfully")
                return True
            else:
                logger.error("❌ Session refresh failed")
                return False

        except Exception as e:
            logger.error(f"❌ Session refresh error: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """
        Check if already logged in to Bitwarden
        
        Returns:
            True if logged in, False otherwise
        """
        try:
            # Try to get status without triggering login
            stdout, stderr = self._run_bw_command(["status"])
            
            if stdout:
                status_data = json.loads(stdout)
                logged_in = status_data.get("status") == "unlocked" or status_data.get("status") == "locked"
                if logged_in:
                    logger.info("✅ Already logged in to Bitwarden")
                    return True
                else:
                    logger.info("🔐 Not logged in to Bitwarden")
                    return False
            else:
                logger.info("🔐 Not logged in to Bitwarden")
                return False
                
        except (BitwardenCLIError, json.JSONDecodeError):
            logger.info("🔐 Not logged in to Bitwarden")
            return False

    def login(self) -> bool:
        """
        Login to Bitwarden using environment credentials
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            # Check if already logged in first
            if self.is_logged_in():
                logger.info("✅ Already logged in, skipping login")
                return True
            
            if not self.email or not self.password:
                logger.error("❌ Bitwarden credentials not configured")
                return False
            
            logger.info(f"🔐 Logging in to Bitwarden as: {self.email}")
            
            # Login and get session key
            stdout, stderr = self._run_bw_command([
                "login", self.email, self.password, "--raw"
            ])
            
            if stdout:
                self.session_key = stdout
                logger.info("✅ Successfully logged in to Bitwarden")
                return True
            else:
                logger.error(f"❌ Login failed: {stderr}")
                return False
                
        except BitwardenCLIError as e:
            logger.error(f"❌ Login failed: {e}")
            return False

    def login_with_2fa(self) -> bool:
        """
        Login to Bitwarden with Two-Factor Authentication support
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            # Check if already logged in first
            if self.is_logged_in():
                logger.info("✅ Already logged in, skipping login")
                return True
            
            if not self.email or not self.password:
                logger.error("❌ Bitwarden credentials not configured")
                return False
            
            logger.info(f"🔐 Logging in to Bitwarden as: {self.email}")
            
            # First try normal login to trigger 2FA email
            logger.info("📧 Sending login request to trigger 2FA email...")
            try:
                stdout, stderr = self._run_bw_command([
                    "login", self.email, self.password, "--raw"
                ], capture_output=False)
            except BitwardenCLIError:
                # This is expected - it will trigger 2FA and wait for code
                pass
            
            # Ask user for 2FA code
            logger.info("📧 Check your email for the Two-Factor Authentication code")
            two_factor_code = input("🔢 Enter the Two-Factor Authentication code from your email: ").strip()
            
            if not two_factor_code:
                logger.error("❌ No Two-Factor Authentication code provided")
                return False
            
            # Now complete login with 2FA code
            logger.info("🔐 Completing login with 2FA code...")
            stdout, stderr = self._run_bw_command([
                "login", self.email, self.password, "--method", "0", "--code", two_factor_code, "--raw"
            ])
            
            if stdout and stdout.strip():
                self.session_key = stdout.strip()
                # Set BW_SESSION environment variable for future commands
                os.environ['BW_SESSION'] = self.session_key
                logger.info("✅ Successfully logged in to Bitwarden with 2FA")
                logger.info(f"🔑 BW_SESSION environment variable set: {self.session_key[:20]}...")
                return True
            else:
                logger.error(f"❌ Login with 2FA failed: {stderr}")
                return False
                
        except BitwardenCLIError as e:
            logger.error(f"❌ Login with 2FA failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during 2FA login: {e}")
            return False
        except KeyboardInterrupt:
            logger.info("❌ Login cancelled by user")
            return False

    def unlock(self) -> bool:
        """
        Unlock the vault using master password and establish persistent session

        Returns:
            True if unlock successful, False otherwise
        """
        try:
            if not self.password:
                logger.error("❌ Bitwarden password not configured")
                return False

            logger.info("🔓 Unlocking Bitwarden vault...")

            # Use --raw flag to get session token directly
            stdout, stderr = self._run_bw_command([
                "unlock", self.password, "--raw"
            ], force_session=False)  # Don't require existing session for unlock

            if stdout and stdout.strip():
                self.session_key = stdout.strip()

                # Set BW_SESSION in environment for ALL processes
                os.environ['BW_SESSION'] = self.session_key

                # Save session to file for persistence
                try:
                    with open('.bw_session', 'w') as f:
                        f.write(self.session_key)
                    logger.info("💾 Session saved to .bw_session file")
                except Exception as e:
                    logger.warning(f"Could not save session to file: {e}")

                # Verify session works
                if self._is_session_valid():
                    logger.info("✅ Successfully unlocked Bitwarden vault with persistent session")
                    logger.info(f"🔑 BW_SESSION set for all processes: {self.session_key[:20]}...")
                    return True
                else:
                    logger.error("❌ Session validation failed after unlock")
                    return False
            else:
                logger.error(f"❌ Unlock failed: {stderr}")
                return False

        except BitwardenCLIError as e:
            logger.error(f"❌ Unlock failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unlock failed: {str(e)}")
            return False
    
    def get_collections(self) -> List[Dict[str, Any]]:
        """
        Get all collections accessible to the user

        Returns:
            List of collection dictionaries
        """
        try:
            stdout, stderr = self._run_bw_command(["list", "collections"])

            if stdout:
                collections = json.loads(stdout)
                logger.info(f"📋 Retrieved {len(collections)} collections")
                return collections
            else:
                logger.warning("⚠️ No collections found")
                return []

        except BitwardenCLIError as e:
            logger.error(f"❌ Failed to get collections: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse collections JSON: {e}")
            return []
    
    def get_collection_items(self, collection_id: str) -> List[Dict[str, Any]]:
        """
        Get all items in a specific collection
        
        Args:
            collection_id: ID of the collection
            
        Returns:
            List of item dictionaries
        """
        try:
            if not self.session_key:
                if not self.unlock():
                    return []
            
            stdout, stderr = self._run_bw_command([
                "list", "items", "--collectionid", collection_id
            ])
            
            if stdout:
                items = json.loads(stdout)
                logger.info(f"📋 Retrieved {len(items)} items from collection")
                return items
            else:
                logger.warning(f"⚠️ No items found in collection {collection_id}")
                return []
                
        except BitwardenCLIError as e:
            logger.error(f"❌ Failed to get collection items: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse items JSON: {e}")
            return []
    
    def get_api_key(self, key_name: str, collection_name: str = "Vyftec Agenten") -> Optional[str]:
        """
        Get API key from Bitwarden by name

        Args:
            key_name: Name of the API key item
            collection_name: Collection to search in (default: Shared-API-Keys)

        Returns:
            API key value or None if not found
        """
        # HARDCODED NOTION KEY FOR TESTING
        if key_name.lower() in ['notion', 'notion-integration', 'notion-api']:
            logger.info("🔧 Using hardcoded Notion API key for testing")
            return ""

        try:
            if not self.session_key:
                if not self.unlock():
                    return None

            # Get collections to find the target collection
            collections = self.get_collections()
            target_collection = None

            for collection in collections:
                if collection.get('name') == collection_name:
                    target_collection = collection
                    break

            if not target_collection:
                logger.warning(f"⚠️ Collection '{collection_name}' not found")
                return None

            # Get items from the collection
            items = self.get_collection_items(target_collection['id'])

            for item in items:
                if item.get('name') == key_name:
                    # Extract the password/API key from the item
                    if 'login' in item and 'password' in item['login']:
                        api_key = item['login']['password']
                        logger.info(f"✅ Retrieved API key: {key_name}")
                        return api_key
                    elif 'notes' in item:
                        # Fallback: check notes field
                        api_key = item['notes']
                        logger.info(f"✅ Retrieved API key from notes: {key_name}")
                        return api_key

            logger.warning(f"⚠️ API key '{key_name}' not found in collection '{collection_name}'")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to retrieve API key '{key_name}': {e}")
            return None
    
    def list_available_keys(self, collection_name: str = "Vyftec Agenten") -> List[str]:
        """
        List all available API keys in a collection
        
        Args:
            collection_name: Collection to list keys from
            
        Returns:
            List of available key names
        """
        try:
            collections = self.get_collections()
            target_collection = None
            
            for collection in collections:
                if collection.get('name') == collection_name:
                    target_collection = collection
                    break
            
            if not target_collection:
                return []
            
            items = self.get_collection_items(target_collection['id'])
            key_info = [f"{item.get('name', 'Unknown')} (ID: {item.get('id', 'N/A')})" for item in items]

            logger.info(f"📋 Available keys in '{collection_name}': {key_info}")
            return key_info
            
        except Exception as e:
            logger.error(f"❌ Failed to list available keys: {e}")
            return []
    
    def sync(self) -> bool:
        """
        Sync Bitwarden vault with server
        
        Returns:
            True if sync successful, False otherwise
        """
        try:
            logger.info("🔄 Syncing Bitwarden vault...")
            stdout, stderr = self._run_bw_command(["sync"])
            
            if "Syncing complete." in stdout or not stderr:
                logger.info("✅ Sync completed successfully")
                return True
            else:
                logger.error(f"❌ Sync failed: {stderr}")
                return False
                
        except BitwardenCLIError as e:
            logger.error(f"❌ Sync failed: {e}")
            return False
    
    def logout(self) -> bool:
        """
        Logout from Bitwarden and clear session
        
        Returns:
            True if logout successful, False otherwise
        """
        try:
            logger.info("🚪 Logging out from Bitwarden...")
            stdout, stderr = self._run_bw_command(["logout"])
            
            self.session_key = None
            logger.info("✅ Successfully logged out from Bitwarden")
            return True
            
        except BitwardenCLIError as e:
            logger.error(f"❌ Logout failed: {e}")
            return False

    # CRUD Operations for Items
    def create_password_item(self, name: str, username: str, password: str, 
                           notes: str = "", collection_id: str = None) -> Optional[str]:
        """
        Create a new password item in Bitwarden
        
        Args:
            name: Item name
            username: Username
            password: Password
            notes: Optional notes
            collection_id: Optional collection ID
            
        Returns:
            Item ID if successful, None otherwise
        """
        try:
            if not self.session_key:
                if not self.unlock():
                    return None
            
            item_data = {
                "type": 1,  # Login type
                "name": name,
                "login": {
                    "username": username,
                    "password": password
                },
                "notes": notes
            }
            
            # Create temporary file for item data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(item_data, f)
                temp_file = f.name
            
            try:
                # Create item
                stdout, stderr = self._run_bw_command([
                    "create", "item", f"@{temp_file}"
                ])
                
                if stdout:
                    item = json.loads(stdout)
                    item_id = item.get('id')
                    
                    # Add to collection if specified
                    if collection_id and item_id:
                        self._add_item_to_collection(item_id, collection_id)
                    
                    logger.info(f"✅ Created password item: {name}")
                    return item_id
                else:
                    logger.error(f"❌ Failed to create password item: {stderr}")
                    return None
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_file)
                
        except Exception as e:
            logger.error(f"❌ Failed to create password item: {e}")
            return None

    def create_note_item(self, name: str, notes: str, collection_id: str = None) -> Optional[str]:
        """
        Create a new secure note item in Bitwarden
        
        Args:
            name: Item name
            notes: Note content
            collection_id: Optional collection ID
            
        Returns:
            Item ID if successful, None otherwise
        """
        try:
            if not self.session_key:
                if not self.unlock():
                    return None
            
            item_data = {
                "type": 2,  # Secure Note type
                "name": name,
                "notes": notes
            }
            
            # Create temporary file for item data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(item_data, f)
                temp_file = f.name
            
            try:
                # Create item
                stdout, stderr = self._run_bw_command([
                    "create", "item", f"@{temp_file}"
                ])
                
                if stdout:
                    item = json.loads(stdout)
                    item_id = item.get('id')
                    
                    # Add to collection if specified
                    if collection_id and item_id:
                        self._add_item_to_collection(item_id, collection_id)
                    
                    logger.info(f"✅ Created note item: {name}")
                    return item_id
                else:
                    logger.error(f"❌ Failed to create note item: {stderr}")
                    return None
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_file)
                
        except Exception as e:
            logger.error(f"❌ Failed to create note item: {e}")
            return None

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get item details by ID
        
        Args:
            item_id: Item ID
            
        Returns:
            Item dictionary or None if not found
        """
        try:
            if not self.session_key:
                if not self.unlock():
                    return None
            
            stdout, stderr = self._run_bw_command([
                "get", "item", item_id
            ])
            
            if stdout:
                item = json.loads(stdout)
                logger.info(f"✅ Retrieved item: {item.get('name', 'Unknown')}")
                return item
            else:
                logger.warning(f"⚠️ Item not found: {item_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get item: {e}")
            return None

    def update_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing item
        
        Args:
            item_id: Item ID
            updates: Dictionary with fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.session_key:
                if not self.unlock():
                    return False
            
            # Get current item
            current_item = self.get_item(item_id)
            if not current_item:
                return False
            
            # Apply updates
            for key, value in updates.items():
                if key in current_item:
                    current_item[key] = value
                elif '.' in key:
                    # Handle nested keys (e.g., 'login.username')
                    keys = key.split('.')
                    current = current_item
                    for k in keys[:-1]:
                        if k not in current:
                            current[k] = {}
                        current = current[k]
                    current[keys[-1]] = value
            
            # Create temporary file for updated item data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(current_item, f)
                temp_file = f.name
            
            try:
                # Update item
                stdout, stderr = self._run_bw_command([
                    "edit", "item", item_id, f"@{temp_file}"
                ])
                
                if stdout:
                    logger.info(f"✅ Updated item: {item_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to update item: {stderr}")
                    return False
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_file)
                
        except Exception as e:
            logger.error(f"❌ Failed to update item: {e}")
            return False

    def delete_item(self, item_id: str) -> bool:
        """
        Delete an item
        
        Args:
            item_id: Item ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.session_key:
                if not self.unlock():
                    return False
            
            stdout, stderr = self._run_bw_command([
                "delete", "item", item_id
            ])
            
            if not stderr:
                logger.info(f"✅ Deleted item: {item_id}")
                return True
            else:
                logger.error(f"❌ Failed to delete item: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to delete item: {e}")
            return False

    def search_items(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for items by name or content
        
        Args:
            search_term: Search term
            
        Returns:
            List of matching items
        """
        try:
            if not self.session_key:
                if not self.unlock():
                    return []
            
            stdout, stderr = self._run_bw_command([
                "list", "items", "--search", search_term
            ])
            
            if stdout:
                items = json.loads(stdout)
                logger.info(f"🔍 Found {len(items)} items matching: {search_term}")
                return items
            else:
                logger.info(f"🔍 No items found matching: {search_term}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to search items: {e}")
            return []

    # Folder Operations
    def create_folder(self, name: str) -> Optional[str]:
        """
        Create a new folder
        
        Args:
            name: Folder name
            
        Returns:
            Folder ID if successful, None otherwise
        """
        try:
            if not self.session_key:
                if not self.unlock():
                    return None
            
            folder_data = {
                "name": name
            }
            
            # Create temporary file for folder data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(folder_data, f, indent=2)
                temp_file = f.name
            
            try:
                # Create folder
                stdout, stderr = self._run_bw_command([
                    "create", "folder", f"@{temp_file}"
                ])
                
                if stdout:
                    folder = json.loads(stdout)
                    folder_id = folder.get('id')
                    logger.info(f"✅ Created folder: {name}")
                    return folder_id
                else:
                    logger.error(f"❌ Failed to create folder: {stderr}")
                    return None
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_file)
                
        except Exception as e:
            logger.error(f"❌ Failed to create folder: {e}")
            return None

    def get_folders(self) -> List[Dict[str, Any]]:
        """
        Get all folders
        
        Returns:
            List of folder dictionaries
        """
        try:
            if not self.session_key:
                if not self.unlock():
                    return []
            
            stdout, stderr = self._run_bw_command(["list", "folders"])
            
            if stdout:
                folders = json.loads(stdout)
                logger.info(f"📁 Retrieved {len(folders)} folders")
                return folders
            else:
                logger.warning("⚠️ No folders found")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to get folders: {e}")
            return []

    def _add_item_to_collection(self, item_id: str, collection_id: str) -> bool:
        """
        Add item to collection (internal helper)
        
        Args:
            item_id: Item ID
            collection_id: Collection ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            stdout, stderr = self._run_bw_command([
                "share", item_id, collection_id
            ])
            
            if not stderr:
                logger.info(f"✅ Added item {item_id} to collection {collection_id}")
                return True
            else:
                logger.error(f"❌ Failed to add item to collection: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to add item to collection: {e}")
            return False


# Helper functions for common operations
def get_github_token() -> Optional[str]:
    """Get GitHub API token from Bitwarden using CLI"""
    client = BitwardenCLIIntegration()
    return client.get_api_key("GitHub-Token")


def get_openai_key() -> Optional[str]:
    """Get OpenAI API key from Bitwarden using CLI"""
    client = BitwardenCLIIntegration()
    return client.get_api_key("OpenAI-Key")


def get_notion_token() -> Optional[str]:
    """Get Notion API token from Bitwarden using CLI"""
    client = BitwardenCLIIntegration()
    return client.get_api_key("Notion-Integration")


def list_shared_api_keys() -> List[str]:
    """List all available API keys in Vyftec Agenten collection using CLI"""
    client = BitwardenCLIIntegration()
    return client.list_available_keys("Vyftec Agenten")


def test_bitwarden_cli_connection() -> Dict[str, Any]:
    """
    Test Bitwarden CLI connection and functionality
    
    Returns:
        Dictionary with test results
    """
    results = {
        "bw_installed": False,
        "login_successful": False,
        "collections_accessible": False,
        "api_keys_retrievable": False,
        "error": None
    }
    
    try:
        client = BitwardenCLIIntegration()
        results["bw_installed"] = True
        
        # Try login first, then unlock
        if client.login() or client.unlock():
            results["login_successful"] = True
            
            collections = client.get_collections()
            if collections:
                results["collections_accessible"] = True
            
            # Test retrieving a common API key
            test_key = client.get_api_key("GitHub-Token")
            if test_key:
                results["api_keys_retrievable"] = True
        
    except Exception as e:
        results["error"] = str(e)
    
    return results


# Test function
if __name__ == "__main__":
    # Test the CLI integration
    print("🔍 Testing Bitwarden CLI Integration...")
    
    # Test connection
    test_results = test_bitwarden_cli_connection()
    print("🔧 Connection Test Results:")
    for key, value in test_results.items():
        print(f"  {key}: {value}")
    
    if test_results["bw_installed"] and test_results["login_successful"]:
        client = BitwardenCLIIntegration()
        
        # List available keys
        keys = list_shared_api_keys()
        print(f"📋 Available keys: {keys}")
        
        # Try to get GitHub token
        github_token = get_github_token()
        if github_token:
            print(f"✅ GitHub token retrieved: {github_token[:10]}...")
        else:
            print("❌ GitHub token not found")
        
        # Sync vault
        if client.sync():
            print("✅ Sync completed")
        else:
            print("❌ Sync failed")
        
        # Logout
        if client.logout():
            print("✅ Logout completed")
        else:
            print("❌ Logout failed")
