# Data Directory

This directory contains all application data including:

## Database
- `attendance_system.db` - SQLite database (auto-created on first run)

## Face Data
- `faces/` - Captured face images from registration
- `encodings/` - Processed face encodings for recognition

## Important Notes
- Database is automatically created when application starts
- Face images and encodings are excluded from version control for privacy
- Backup this directory regularly in production environments

**Privacy**: This directory contains biometric data. Handle according to your local privacy regulations.
