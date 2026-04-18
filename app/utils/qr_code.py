"""QR code generator utility."""

import base64
from io import BytesIO

import pyqrcode


def generate_qr_code(data: str, size: int = 10) -> str:
    """
    Generate a QR code and return as base64-encoded PNG.

    Args:
        data: Data to encode in QR code
        size: QR code size (1-40, default 10)

    Returns:
        Base64-encoded PNG image
    """
    qr = pyqrcode.create(data, error="M")
    buffer = BytesIO()
    qr.png(buffer, scale=size)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


def generate_qr_code_svg(data: str) -> str:
    """
    Generate a QR code and return as SVG string.

    Args:
        data: Data to encode in QR code

    Returns:
        SVG string
    """
    qr = pyqrcode.create(data, error="M")
    return qr.svg_lxml()


def generate_login_qr_url(ticket: str, size: int = 200) -> str:
    """
    Generate a QR code image URL for login.

    This creates a URL that can be used to display a QR code.

    Args:
        ticket: Login ticket
        size: QR code size in pixels

    Returns:
        URL for QR code image
    """
    # Using a public QR code generation service
    data = f"wechat:login:{ticket}"
    return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={data}"


def validate_qr_ticket(ticket: str) -> bool:
    """
    Validate a QR ticket format.

    Args:
        ticket: Ticket string

    Returns:
        True if valid format
    """
    import uuid

    try:
        uuid.UUID(ticket)
        return True
    except (ValueError, AttributeError):
        return False
