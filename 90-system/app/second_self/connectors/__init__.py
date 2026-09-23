"""Provider-neutral contracts and optional external connector boundaries."""

from .contracts import (
    ConnectorItem,
    ConnectorKind,
    ConnectorRequest,
    ConnectorResult,
    ConnectorState,
)
from .drive_auth import (
    DRIVE_READONLY_SCOPE,
    DriveAuthError,
    DriveCredentialStore,
    authorize_drive,
    load_drive_credentials,
)
from .gmail_auth import (
    GMAIL_READONLY_SCOPE,
    GmailAuthError,
    GmailCredentialStore,
    authorize_gmail,
    load_gmail_credentials,
)

__all__ = [
    "ConnectorItem",
    "ConnectorKind",
    "ConnectorRequest",
    "ConnectorResult",
    "ConnectorState",
    "GMAIL_READONLY_SCOPE",
    "GmailAuthError",
    "GmailCredentialStore",
    "authorize_gmail",
    "load_gmail_credentials",
    "DRIVE_READONLY_SCOPE",
    "DriveAuthError",
    "DriveCredentialStore",
    "authorize_drive",
    "load_drive_credentials",
]
