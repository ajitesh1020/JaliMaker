#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JaliMaker - CNC Grill/Jali Drill GCode Generator
Company: Ajitesh Kannojia
License: MIT License
Author: Ajitesh Kannojia
Version: See core/version.py
"""

import sys
import os
import logging
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from core.config_manager import ConfigManager
from core.logger import setup_logger
from core.version import VERSION, APP_NAME
from ui.main_window import MainWindow


def main():
    """Application entry point"""
    # Setup logging before anything else
    config = ConfigManager()
    logger = setup_logger(config.get_bool("SECURITY", "dev_mode", False))

    logger.info(f"{'='*60}")
    logger.info(f"Starting {APP_NAME} v{VERSION}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"{'='*60}")

    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("Indus Robotics")

    # High DPI is on by default in Qt6 – AA_UseHighDpiPixmaps is deprecated

    # Create and show main window
    try:
        window = MainWindow(config, logger)
        window.show()
        logger.info("Main window displayed successfully")
        exit_code = app.exec()
    except Exception as e:
        logger.critical(f"Fatal error starting application: {e}", exc_info=True)
        exit_code = 1

    logger.info(f"Application exiting with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
