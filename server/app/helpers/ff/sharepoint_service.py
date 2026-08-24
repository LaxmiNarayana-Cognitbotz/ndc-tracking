import asyncio
import io
import logging
import os
import urllib.parse
import zipfile
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import httpx
import msal
import requests
import urllib3

# Suppress insecure request warnings when SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

def _resolve_ssl_verify():
    """
    Resolves whether SSL verification should be enabled based on environment
    variables: SHAREPOINT_SSL_VERIFY, SSL_VERIFY, PROXY_INSECURE_SSL.
    Returns True, False, or a string path to a CA bundle.
    """
    try:
        verify = True

        # Check general proxy SSL setting first
        proxy_insecure = os.getenv("PROXY_INSECURE_SSL", "false").lower() in ("true", "1", "yes", "on")
        if proxy_insecure:
            verify = False

        # Allow more specific overrides
        verify_val = os.getenv("SHAREPOINT_SSL_VERIFY")
        if verify_val is None:
            verify_val = os.getenv("SSL_VERIFY")

        if verify_val is not None:
            val_lower = verify_val.strip().lower()
            if val_lower in ("false", "0", "no", "off"):
                verify = False
            elif val_lower in ("true", "1", "yes", "on"):
                verify = True
            else:
                # Treat as path to a custom CA bundle
                verify = verify_val

        return verify
    except Exception as e:
        logger.error(f"Error in _resolve_ssl_verify: {e}", exc_info=True)
        return True

def _get_msal_http_client() -> requests.Session:
    """
    Returns a requests.Session with SSL verification settings matching
    the environment configuration. Used as the http_client for MSAL to
    ensure token acquisition works behind corporate SSL-intercepting proxies.
    """
    try:
        session = requests.Session()
        session.verify = _resolve_ssl_verify()
        return session
    except Exception as e:
        logger.error(f"Error in _get_msal_http_client: {e}", exc_info=True)
        raise

def get_httpx_client(*args, **kwargs) -> httpx.AsyncClient:
    """
    Creates an httpx.AsyncClient with SSL verification optionally disabled or customized
    via environment variables (SHAREPOINT_SSL_VERIFY, SSL_VERIFY, or PROXY_INSECURE_SSL).
    Also supports custom proxies configured via PROXY_ENABLED and PROXY_URL.
    """
    try:
        if "verify" not in kwargs:
            kwargs["verify"] = _resolve_ssl_verify()

        # Proxy Configuration
        proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() in ("true", "1", "yes", "on")
        proxy_url = os.getenv("PROXY_URL")
        if proxy_enabled and proxy_url and "proxy" not in kwargs:
            kwargs["proxy"] = proxy_url

        return httpx.AsyncClient(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in get_httpx_client: {e}", exc_info=True)
        raise

class SharePointService:
    def __init__(self):
        try:
            # Cached properties to avoid repeating site/drive lookups
            self._site_id: Optional[str] = None
            self._drive_id: Optional[str] = None
        except Exception as e:
            logger.error(f"Error in SharePointService.__init__: {e}", exc_info=True)

    @property
    def tenant_id(self) -> str:
        try:
            val = os.getenv("SHAREPOINT_TENANT_ID")
            if not val:
                raise Exception("SHAREPOINT_TENANT_ID environment variable is missing.")
            return val
        except Exception as e:
            logger.error(f"Error in tenant_id: {e}", exc_info=True)
            raise

    @property
    def client_id(self) -> str:
        try:
            val = os.getenv("SHAREPOINT_CLIENT_ID")
            if not val:
                raise Exception("SHAREPOINT_CLIENT_ID environment variable is missing.")
            return val
        except Exception as e:
            logger.error(f"Error in client_id: {e}", exc_info=True)
            raise

    @property
    def client_secret(self) -> str:
        try:
            val = os.getenv("SHAREPOINT_CLIENT_SECRET")
            if not val:
                raise Exception("SHAREPOINT_CLIENT_SECRET environment variable is missing.")
            return val
        except Exception as e:
            logger.error(f"Error in client_secret: {e}", exc_info=True)
            raise

    @property
    def site_url(self) -> str:
        try:
            val = os.getenv("SHAREPOINT_SITE_URL")
            if not val:
                raise Exception("SHAREPOINT_SITE_URL environment variable is missing.")
            return val
        except Exception as e:
            logger.error(f"Error in site_url: {e}", exc_info=True)
            raise

    @property
    def target_folder(self) -> str:
        try:
            val = os.getenv("SHAREPOINT_TARGET_FOLDER")
            if not val:
                raise Exception("SHAREPOINT_TARGET_FOLDER environment variable is missing.")
            return val
        except Exception as e:
            logger.error(f"Error in target_folder: {e}", exc_info=True)
            raise

    @property
    def authority(self) -> str:
        try:
            return f"https://login.microsoftonline.com/{self.tenant_id}"
        except Exception as e:
            logger.error(f"Error in authority: {e}", exc_info=True)
            raise

    @property
    def scopes(self) -> list[str]:
        try:
            return ["https://graph.microsoft.com/.default"]
        except Exception as e:
            logger.error(f"Error in scopes: {e}", exc_info=True)
            raise

    async def get_access_token(self) -> str:
        """Obtain a Microsoft Graph API access token using client credentials flow."""
        try:
            if not self.tenant_id or not self.client_id or not self.client_secret:
                raise Exception("SharePoint credentials are not configured in environment variables.")

            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret,
                http_client=_get_msal_http_client()
            )
            
            # First check MSAL internal cache
            result = app.acquire_token_silent(self.scopes, account=None)
            if not result:
                logger.info("No cached token found. Requesting a new token from Azure AD.")
                # Run the synchronous token fetch in a thread pool to keep FastAPI non-blocking
                result = await asyncio.to_thread(
                    app.acquire_token_for_client,
                    scopes=self.scopes
                )
                
            if "access_token" in result:
                return result["access_token"]
            else:
                error_msg = result.get("error_description") or result.get("error") or "Unknown error"
                logger.error(f"SharePoint authentication failed: {error_msg}")
                raise Exception(f"SharePoint authentication failed: {error_msg}")
        except Exception as e:
            logger.error(f"Error in get_access_token: {e}", exc_info=True)
            raise

    async def get_site_id(self, client: httpx.AsyncClient) -> str:
        """Resolve the SharePoint Site ID from the SHAREPOINT_SITE_URL."""
        try:
            if self._site_id:
                return self._site_id

            if not self.site_url:
                raise Exception("SHAREPOINT_SITE_URL is not configured.")

            parsed_url = urllib.parse.urlparse(self.site_url)
            hostname = parsed_url.netloc
            relative_path = parsed_url.path.rstrip("/")
            
            token = await self.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Graph API format for sites: sites/{hostname}:/{relative-path}
            url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:{relative_path}"
            logger.info(f"Resolving Site ID from URL: {url}")
            
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to resolve site ID. Status: {response.status_code}, Body: {response.text}")
                raise Exception(f"Failed to resolve site ID: {response.status_code} - {response.text}")
                
            site_data = response.json()
            self._site_id = site_data.get("id")
            if not self._site_id:
                raise Exception("Site details resolved but 'id' field is missing.")
                
            logger.info(f"Resolved Site ID: {self._site_id}")
            return self._site_id
        except Exception as e:
            logger.error(f"Error in get_site_id: {e}", exc_info=True)
            raise

    async def get_drive_details(self, client: httpx.AsyncClient, site_id: str) -> Tuple[str, str]:
        """
        Resolves the Drive ID (Document Library ID) and the base folder path inside that drive
        from the SHAREPOINT_TARGET_FOLDER environment variable.
        """
        try:
            if self._drive_id:
                # Recompute folder path since it depends on target_folder
                pass

            if not self.target_folder:
                raise Exception("SHAREPOINT_TARGET_FOLDER is not configured.")

            # Determine relative folder after the site prefix
            parsed_site = urllib.parse.urlparse(self.site_url)
            site_path = parsed_site.path.rstrip("/")
            
            folder = self.target_folder
            if folder.startswith(site_path):
                folder = folder[len(site_path):]
            folder = folder.strip("/")
            
            # Split target folder path. e.g. "Shared Documents/AI_AGEL/001_AI_Project/AI05_NDC_Tracker"
            parts = [p for p in folder.split("/") if p]
            if not parts:
                drive_name = "Shared Documents"
                folder_path_in_drive = ""
            else:
                drive_name = parts[0]
                folder_path_in_drive = "/".join(parts[1:])
                
            logger.info(f"Target drive name: '{drive_name}', path inside drive: '{folder_path_in_drive}'")
            
            token = await self.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Fetch drives list to map drive_name to drive_id
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to list drives. Status: {response.status_code}, Body: {response.text}")
                raise Exception(f"Failed to list drives: {response.status_code}")
                
            drives = response.json().get("value", [])
            drive_id = None
            for d in drives:
                name = d.get("name")
                if name == drive_name or (drive_name == "Shared Documents" and name == "Documents") or (drive_name == "Documents" and name == "Shared Documents"):
                    drive_id = d.get("id")
                    break
                    
            if not drive_id:
                logger.warning(f"Drive '{drive_name}' not found in drives list. Falling back to site default drive.")
                default_drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
                res = await client.get(default_drive_url, headers=headers)
                if res.status_code == 200:
                    drive_id = res.json().get("id")
                else:
                    raise Exception(f"Failed to resolve document library '{drive_name}' or site default drive: {res.text}")
                    
            self._drive_id = drive_id
            logger.info(f"Resolved Drive ID: {self._drive_id}")
            return drive_id, folder_path_in_drive
        except Exception as e:
            logger.error(f"Error in get_drive_details: {e}", exc_info=True)
            raise

    def _encode_path_segments(self, path: str) -> str:
        """Safely URL-encodes each path segment individually, preserving slashes."""
        try:
            segments = [urllib.parse.quote(s) for s in path.split("/") if s]
            return "/".join(segments)
        except Exception as e:
            logger.error(f"Error in _encode_path_segments: {e}", exc_info=True)
            raise

    async def get_person_folder_files(
        self, client: httpx.AsyncClient, site_id: str, drive_id: str, folder_path_in_drive: str, person_number: str
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Locates the employee folder by person number and lists all files within it.
        Checks multiple candidate paths to support cases with or without a nested 'F&F_Documents' directory.
        Returns a tuple: (list of file items, successfully resolved folder path).
        """
        try:
            token = await self.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # We check two main path structures:
            # 1. {folder_path_in_drive}/F&F_Documents/{person_number} (most likely structure)
            # 2. {folder_path_in_drive}/{person_number} (fallback structure)
            candidates = []
            if folder_path_in_drive:
                if "F&F_Documents" not in folder_path_in_drive:
                    candidates.append(f"{folder_path_in_drive}/F&F_Documents/{person_number}")
                candidates.append(f"{folder_path_in_drive}/{person_number}")
            else:
                candidates.append(f"F&F_Documents/{person_number}")
                candidates.append(person_number)

            async def fetch_candidate(candidate_path):
                try:
                    clean_path = "/".join([p for p in candidate_path.split("/") if p])
                    encoded_path = self._encode_path_segments(clean_path)
                    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{encoded_path}:/children"
                    logger.info(f"Querying SharePoint path: {clean_path} (Encoded: {encoded_path})")
                    response = await client.get(url, headers=headers)
                    return response, clean_path
                except Exception as e:
                    logger.error(f"Error in fetch_candidate for {candidate_path}: {e}")
                    raise

            tasks = [fetch_candidate(cp) for cp in candidates]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    continue
                response, clean_path = result
                if response.status_code == 200:
                    children = response.json().get("value", [])
                    files = [item for item in children if "file" in item]
                    logger.info(f"Folder '{clean_path}' found with {len(files)} files.")
                    return files, clean_path

            # If none matched, check if there was an auth error
            for result in results:
                if isinstance(result, tuple):
                    response, clean_path = result
                    if response.status_code not in (200, 404):
                        logger.error(f"Error querying path '{clean_path}': {response.status_code} - {response.text}")
                        if response.status_code in (401, 403):
                            raise Exception(f"SharePoint permissions or auth error: {response.text}")
                        
            # If all candidates returned 404
            return [], ""
        except Exception as e:
            logger.error(f"Error in get_person_folder_files: {e}", exc_info=True)
            raise

    async def get_download_stream(
        self, file_item: Dict[str, Any]
    ) -> Tuple[AsyncGenerator[bytes, None], str, str]:
        """
        Extracts details from file item and returns an async byte generator, filename, and mimetype.
        """
        try:
            download_url = file_item.get("@microsoft.graph.downloadUrl")
            file_name = file_item.get("name", "document.pdf")
            mime_type = file_item.get("file", {}).get("mimeType", "application/octet-stream")
            
            if not download_url:
                raise Exception("SharePoint file item is missing download URL.")
                
            logger.info(f"Preparing download stream for file: '{file_name}' (MIME: {mime_type})")
            
            # Generator function that streams file chunk-by-chunk using a self-managed httpx client
            async def stream_generator():
                try:
                    async with get_httpx_client() as dl_client:
                        async with dl_client.stream("GET", download_url) as r:
                            r.raise_for_status()
                            async for chunk in r.aiter_bytes(chunk_size=8192):
                                yield chunk
                except Exception as e:
                    logger.error(f"Error in stream_generator: {e}")
                    raise
                        
            return stream_generator(), file_name, mime_type
        except Exception as e:
            logger.error(f"Error in get_download_stream: {e}", exc_info=True)
            raise

    async def get_zipped_download_stream(
        self, files: List[Dict[str, Any]], person_number: str
    ) -> Tuple[AsyncGenerator[bytes, None], str, str]:
        """
        Downloads multiple files from SharePoint, compiles them into a ZIP archive,
        and returns an async byte generator for the ZIP content.
        """
        try:
            zip_filename = f"{person_number}_documents.zip"
            mime_type = "application/zip"
            
            logger.info(f"Creating ZIP download stream for {len(files)} files.")
            
            async def zip_stream_generator():
                try:
                    zip_buffer = io.BytesIO()
                    async def fetch_file(fetch_client, file_item):
                        name = file_item.get("name", "document.pdf")
                        download_url = file_item.get("@microsoft.graph.downloadUrl")
                        if download_url:
                            try:
                                logger.info(f"Fetching '{name}' for zipping...")
                                res = await fetch_client.get(download_url)
                                if res.status_code == 200:
                                    return name, res.content
                                else:
                                    logger.error(f"Failed to fetch '{name}' for zipping (status: {res.status_code})")
                            except Exception as e:
                                logger.error(f"Error fetching '{name}' for zipping: {str(e)}")
                        return None, None

                    # Compile the zip archive in-memory
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        async with get_httpx_client() as fetch_client:
                            tasks = [fetch_file(fetch_client, item) for item in files]
                            fetched_results = await asyncio.gather(*tasks)
                            
                            for name, content in fetched_results:
                                if name and content:
                                    zip_file.writestr(name, content)
                                    logger.info(f"Successfully added '{name}' to ZIP archive.")
                                        
                    zip_buffer.seek(0)
                    # Yield chunk-by-chunk
                    while True:
                        chunk = zip_buffer.read(8192)
                        if not chunk:
                            break
                        yield chunk
                except Exception as e:
                    logger.error(f"Error in zip_stream_generator: {e}")
                    raise
                    
            return zip_stream_generator(), zip_filename, mime_type
        except Exception as e:
            logger.error(f"Error in get_zipped_download_stream: {e}", exc_info=True)
            raise

    async def download_employee_documents(
        self, client: httpx.AsyncClient, person_number: str
    ) -> Dict[str, Any] | None:
        """
        Resolves site, drive, lists employee folder files.
        Returns a dict indicating how to serve the file:
        - {"type": "redirect", "url": download_url} for single files.
        - {"type": "stream", "stream": async_generator, "filename": str, "mime_type": str} for multiple files.
        Returns None if no files are found.
        """
        try:
            # 1. Resolve site ID
            site_id = await self.get_site_id(client)

            # 2. Resolve drive ID and target folder path
            drive_id, folder_path = await self.get_drive_details(client, site_id)

            # 3. Locate folder by person number and list files
            files, resolved_folder = await self.get_person_folder_files(
                client, site_id, drive_id, folder_path, person_number
            )

            if not files:
                return None

            # 4. For a single file, return direct download URL bypass. For multiple, zip them.
            if len(files) == 1:
                selected_file = files[0]
                download_url = selected_file.get("@microsoft.graph.downloadUrl")
                if download_url:
                    logger.info(f"Single file found for {person_number}. Bypassing backend streaming with direct URL.")
                    return {"type": "redirect", "url": download_url}
                else:
                    # Fallback if downloadUrl is missing for some reason
                    stream, filename, mime = await self.get_download_stream(selected_file)
                    return {"type": "stream", "stream": stream, "filename": filename, "mime_type": mime}
            else:
                stream, filename, mime = await self.get_zipped_download_stream(files, person_number)
                return {"type": "stream", "stream": stream, "filename": filename, "mime_type": mime}
        except Exception as e:
            logger.error(f"Error in download_employee_documents: {e}", exc_info=True)
            raise
