"""
Main entry point for Accessible PDF Toolkit.
"""

import sys
import argparse
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from .utils.constants import APP_NAME, APP_VERSION, ensure_directories
from .utils.logger import setup_logging, get_logger
from .database.models import init_db
from .gui.main_window import MainWindow
from .gui.login_dialog import LoginDialog


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="accessible-pdf-toolkit",
        description="Privacy-first PDF accessibility toolkit",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_NAME} {APP_VERSION}",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    parser.add_argument(
        "--no-login",
        action="store_true",
        help="Skip login dialog (for development)",
    )

    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="PDF file to open",
    )

    parser.add_argument(
        "--batch",
        type=Path,
        metavar="DIRECTORY",
        help="Batch process all PDFs in directory",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (for batch processing)",
    )

    return parser.parse_args()


def run_batch_processing(directory: Path) -> int:
    """
    Run batch processing on a directory of PDFs.

    Args:
        directory: Directory containing PDF files

    Returns:
        Exit code
    """
    logger = get_logger(__name__)

    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return 1

    pdf_files = list(directory.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in: {directory}")
        return 0

    logger.info(f"Found {len(pdf_files)} PDF files")

    # Import processing modules
    from .core.pdf_handler import PDFHandler
    from .core.wcag_validator import WCAGValidator

    handler = PDFHandler()
    validator = WCAGValidator()

    success_count = 0
    for pdf_file in pdf_files:
        logger.info(f"Processing: {pdf_file.name}")
        try:
            # Open and validate
            doc = handler.open(pdf_file)
            if doc:
                results = validator.validate(doc)
                logger.info(f"  Compliance score: {results.score:.1f}%")
                success_count += 1
        except Exception as e:
            logger.error(f"  Error: {e}")

    logger.info(f"Processed {success_count}/{len(pdf_files)} files")
    return 0 if success_count == len(pdf_files) else 1


def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code
    """
    args = parse_args()

    # Initialize logging
    import logging
    level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=level)
    logger = get_logger(__name__)

    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

    # Ensure directories exist
    ensure_directories()

    # Initialize database
    init_db()

    # Batch processing mode
    if args.batch:
        return run_batch_processing(args.batch)

    # Headless mode check
    if args.headless:
        logger.error("Headless mode requires --batch option")
        return 1

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Accessible PDF Toolkit")

    # Enable high DPI scaling
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Set application style
    app.setStyle("Fusion")

    user = None

    # Show login dialog (unless skipped)
    if not args.no_login:
        login_dialog = LoginDialog()
        if login_dialog.exec():
            user = login_dialog.get_user()
        else:
            # User cancelled login
            logger.info("Login cancelled")
            return 0

    # Create and show main window
    window = MainWindow(user=user)
    window.show()

    # Open file if provided
    if args.file:
        window.open_file(args.file)

    # Run event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
