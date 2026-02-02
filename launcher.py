#!/usr/bin/env python3
"""
Launcher script for Accessible PDF Toolkit.
This script properly initializes the package for PyInstaller.
"""

import sys
import os

# Add the src directory to the path
if getattr(sys, 'frozen', False):
    # Running as compiled
    base_path = sys._MEIPASS
else:
    # Running as script
    base_path = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(base_path, 'src')
    if os.path.exists(src_path):
        sys.path.insert(0, src_path)

# Now import and run the application
def main():
    import argparse
    from pathlib import Path

    # Parse args first
    parser = argparse.ArgumentParser(
        prog="accessible-pdf-toolkit",
        description="Privacy-first PDF accessibility toolkit",
    )
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-login", action="store_true", help="Skip login dialog")
    parser.add_argument("file", nargs="?", type=Path, help="PDF file to open")
    parser.add_argument("--batch", type=Path, metavar="DIRECTORY", help="Batch process directory")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")

    args = parser.parse_args()

    if args.version:
        print("Accessible PDF Toolkit 1.0.0")
        return 0

    # Setup logging
    import logging
    level = logging.DEBUG if args.debug else logging.INFO

    # Create app data directory
    app_data_dir = Path.home() / ".accessible-pdf-toolkit"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    (app_data_dir / "logs").mkdir(exist_ok=True)
    (app_data_dir / "cache").mkdir(exist_ok=True)
    (app_data_dir / "temp").mkdir(exist_ok=True)

    # Setup basic logging
    log_file = app_data_dir / "logs" / "app.log"
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger("AccessiblePDFToolkit")
    logger.info("Starting Accessible PDF Toolkit v1.0.0")

    # Initialize database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import declarative_base, sessionmaker

    db_path = app_data_dir / "database.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    # Import and create tables
    from accessible_pdf_toolkit.database.models import Base
    Base.metadata.create_all(engine)

    # Batch processing mode
    if args.batch:
        logger.info(f"Batch processing: {args.batch}")
        # Simple batch mode - just list files for now
        if args.batch.exists():
            pdf_files = list(args.batch.glob("*.pdf"))
            logger.info(f"Found {len(pdf_files)} PDF files")
            for f in pdf_files:
                logger.info(f"  - {f.name}")
        return 0

    # Headless mode check
    if args.headless:
        logger.error("Headless mode requires --batch option")
        return 1

    # Start GUI
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("Accessible PDF Toolkit")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Accessible PDF Toolkit")

    # Enable high DPI scaling
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Set application style
    app.setStyle("Fusion")

    # Import GUI components
    from accessible_pdf_toolkit.gui.main_window import MainWindow
    from accessible_pdf_toolkit.gui.login_dialog import LoginDialog

    user = None

    # Show login dialog (unless skipped)
    if not args.no_login:
        login_dialog = LoginDialog()
        if login_dialog.exec():
            user = login_dialog.get_user()
        else:
            logger.info("Login cancelled")
            return 0

    # Create and show main window
    window = MainWindow(user=user)
    window.show()

    # Open file if provided
    if args.file:
        window.open_file(args.file)

    logger.info("Application started successfully")

    # Run event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
