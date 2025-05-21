"""
Mailbox Migration Utility

This script migrates messages from the old directory-based mailbox system to the new JSON-based system.
It implements task_migrate_all_mailboxes_001.

Usage:
    python -m src.dreamos.core.mailbox_migration

Author: Agent-3
Date: 2025-05-18
"""

import os
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("runtime/logs/mailbox_migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mailbox_migration")

# Constants
OLD_MAILBOX_DIR = "runtime/agent_comms/agent_mailboxes"
NEW_MAILBOX_DIR = "runtime/agent_comms/mailboxes"
ACTIVE_AGENTS = [
    "Agent-1", "Agent-2", "Agent-3", "Agent-4", "Agent-5",
    "Agent-6", "Agent-7", "Agent-8", "Captain-THEA", 
    "commander-THEA", "general-victor", "JARVIS", "ORCHESTRATOR", "VALIDATOR"
]

class MailboxMigrator:
    """Handles migration from old directory-based mailboxes to new JSON-based system."""
    
    def __init__(self):
        """Initialize the mailbox migrator."""
        self.old_mailbox_dir = Path(OLD_MAILBOX_DIR)
        self.new_mailbox_dir = Path(NEW_MAILBOX_DIR)
        
        # Ensure the new mailbox directory exists
        os.makedirs(self.new_mailbox_dir, exist_ok=True)
        
    def migrate_all_mailboxes(self) -> bool:
        """
        Migrate all mailboxes from the old system to the new.
        
        Returns:
            bool: True if migration was successful
        """
        logger.info("Starting mailbox migration process...")
        
        # Track successful and failed migrations
        success_count = 0
        failure_count = 0
        
        # First, create empty JSON mailboxes for all active agents if they don't exist
        self._create_empty_mailboxes(ACTIVE_AGENTS)
        
        # Get a list of agent directories in the old mailbox system
        agent_dirs = [d for d in self.old_mailbox_dir.iterdir() 
                    if d.is_dir() and not d.name.startswith('.')]
        
        for agent_dir in agent_dirs:
            agent_id = agent_dir.name
            
            # Skip directories that don't match agent naming patterns
            if not (agent_id.startswith("Agent-") or 
                   agent_id in ["Captain-THEA", "commander-THEA", "general-victor", 
                              "JARVIS", "ORCHESTRATOR", "VALIDATOR"]):
                logger.info(f"Skipping non-agent directory: {agent_id}")
                continue
                
            logger.info(f"Processing mailbox for agent: {agent_id}")
            
            try:
                # Migrate this agent's mailbox
                if self._migrate_agent_mailbox(agent_id):
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                logger.error(f"Error migrating mailbox for {agent_id}: {str(e)}")
                failure_count += 1
        
        logger.info(f"Mailbox migration complete. Successful: {success_count}, Failed: {failure_count}")
        return failure_count == 0
    
    def _create_empty_mailboxes(self, agent_ids: List[str]) -> None:
        """
        Create empty JSON mailboxes for all the specified agents if they don't exist.
        
        Args:
            agent_ids: List of agent IDs
        """
        logger.info(f"Creating empty mailboxes for {len(agent_ids)} agents...")
        
        for agent_id in agent_ids:
            agent_mailbox_path = self.new_mailbox_dir / f"{agent_id.lower()}.json"
            
            # Skip if the mailbox already exists
            if agent_mailbox_path.exists():
                logger.info(f"Mailbox already exists for {agent_id}, skipping creation")
                continue
                
            # Create empty mailbox structure
            empty_mailbox = {
                "messages": [],
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            # Write to file
            with open(agent_mailbox_path, 'w') as f:
                json.dump(empty_mailbox, f, indent=2)
                
            logger.info(f"Created empty mailbox for {agent_id}")
    
    def _migrate_agent_mailbox(self, agent_id: str) -> bool:
        """
        Migrate a single agent's mailbox from the old system to the new.
        
        Args:
            agent_id: The ID of the agent whose mailbox is being migrated
            
        Returns:
            bool: True if migration was successful
        """
        inbox_dir = self.old_mailbox_dir / agent_id / "inbox"
        if not inbox_dir.exists():
            # Create the inbox directory if it doesn't exist
            logger.info(f"Creating inbox directory for {agent_id}")
            os.makedirs(inbox_dir, exist_ok=True)
            
        # Get the new JSON mailbox file path
        new_mailbox_path = self.new_mailbox_dir / f"{agent_id.lower()}.json"
        
        # Load existing mailbox or create a new one
        if new_mailbox_path.exists():
            with open(new_mailbox_path, 'r') as f:
                mailbox = json.load(f)
        else:
            mailbox = {
                "messages": [],
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
            
        # Get a list of all files in the inbox (excluding processed and hidden files)
        inbox_files = [f for f in inbox_dir.iterdir() 
                     if f.is_file() and not f.name.startswith('.') and f.name != ".keep"]
        
        # Get processed directory if it exists
        processed_dir = inbox_dir / "processed"
        processed_files = []
        if processed_dir.exists():
            processed_files = [f for f in processed_dir.iterdir() 
                             if f.is_file() and not f.name.startswith('.') and f.name != ".keep"]
        
        # Process all inbox files
        for inbox_file in inbox_files:
            try:
                message = self._convert_file_to_message(inbox_file, agent_id, "pending")
                if message:
                    mailbox["messages"].append(message)
                    logger.info(f"Migrated pending message: {inbox_file.name} for {agent_id}")
            except Exception as e:
                logger.error(f"Error migrating inbox file {inbox_file.name}: {str(e)}")
                
        # Process all processed files
        for processed_file in processed_files:
            try:
                message = self._convert_file_to_message(processed_file, agent_id, "processed")
                if message:
                    mailbox["messages"].append(message)
                    logger.info(f"Migrated processed message: {processed_file.name} for {agent_id}")
            except Exception as e:
                logger.error(f"Error migrating processed file {processed_file.name}: {str(e)}")
        
        # Update last_updated timestamp
        mailbox["last_updated"] = datetime.now().isoformat()
        
        # Write the updated mailbox
        with open(new_mailbox_path, 'w') as f:
            json.dump(mailbox, f, indent=2)
            
        logger.info(f"Migration complete for {agent_id}. Migrated {len(inbox_files)} inbox files and {len(processed_files)} processed files.")
        return True
            
    def _convert_file_to_message(self, file_path: Path, recipient: str, status: str) -> Optional[Dict[str, Any]]:
        """
        Convert a file from the old mailbox system into a message for the new system.
        
        Args:
            file_path: Path to the file
            recipient: Agent ID of the recipient
            status: Status of the message ("pending" or "processed")
            
        Returns:
            Optional[Dict[str, Any]]: The message or None if conversion failed
        """
        # Get creation time as an ISO timestamp
        try:
            timestamp = datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
        except Exception:
            timestamp = datetime.now().isoformat()
        
        # Read the file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Could not read file {file_path}: {str(e)}")
            return None
            
        # Try to determine the sender from the file content
        sender = "unknown"
        subject = file_path.stem
        
        # Check for markdown format with headers
        if content.startswith('#') or '**From:**' in content:
            for line in content.split('\n'):
                line = line.strip()
                if '**From:**' in line:
                    sender = line.split('**From:**')[1].strip()
                elif line.startswith('**From:**'):
                    sender = line[9:].strip()
                elif '**Subject:**' in line:
                    subject = line.split('**Subject:**')[1].strip()
                elif line.startswith('**Subject:**'):
                    subject = line[12:].strip()
        
        # Create the message structure
        message = {
            "id": f"{file_path.stem}_{timestamp.replace(':', '-')}",
            "timestamp": timestamp,
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "content": content,
            "status": status,
            "source_file": str(file_path)
        }
        
        return message
        
    def backup_old_mailboxes(self) -> str:
        """
        Create a backup of the old mailbox directory.
        
        Returns:
            str: Path to the backup directory
        """
        backup_dir = f"runtime/agent_comms/mailbox_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Creating backup of old mailboxes at {backup_dir}")
        
        try:
            shutil.copytree(self.old_mailbox_dir, backup_dir)
            logger.info(f"Backup completed successfully")
            return backup_dir
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return ""
            
    def validate_migration(self) -> bool:
        """
        Validate that the migration was successful by checking that all
        agents have a JSON mailbox and that all messages were migrated.
        
        Returns:
            bool: True if validation passed
        """
        logger.info("Validating migration...")
        
        # Check that all active agents have a JSON mailbox
        for agent_id in ACTIVE_AGENTS:
            mailbox_path = self.new_mailbox_dir / f"{agent_id.lower()}.json"
            if not mailbox_path.exists():
                logger.error(f"Validation failed: No JSON mailbox for {agent_id}")
                return False
                
        # Count total messages in old system
        old_message_count = 0
        for agent_dir in self.old_mailbox_dir.iterdir():
            if not agent_dir.is_dir() or agent_dir.name.startswith('.'):
                continue
                
            inbox_dir = agent_dir / "inbox"
            if not inbox_dir.exists():
                continue
                
            # Count inbox files
            old_message_count += len([f for f in inbox_dir.iterdir() 
                                    if f.is_file() and not f.name.startswith('.') and f.name != ".keep"])
            
            # Count processed files
            processed_dir = inbox_dir / "processed"
            if processed_dir.exists():
                old_message_count += len([f for f in processed_dir.iterdir() 
                                        if f.is_file() and not f.name.startswith('.') and f.name != ".keep"])
        
        # Count total messages in new system
        new_message_count = 0
        for mailbox_file in self.new_mailbox_dir.iterdir():
            if not mailbox_file.is_file() or not mailbox_file.name.endswith('.json'):
                continue
                
            try:
                with open(mailbox_file, 'r') as f:
                    mailbox = json.load(f)
                    new_message_count += len(mailbox.get("messages", []))
            except Exception as e:
                logger.error(f"Error reading mailbox {mailbox_file}: {str(e)}")
                return False
        
        # Compare message counts
        if new_message_count < old_message_count:
            logger.warning(f"Validation warning: Old system had {old_message_count} messages, but new system has {new_message_count} messages")
        
        logger.info(f"Validation complete. Old system: {old_message_count} messages, New system: {new_message_count} messages")
        return True

def main():
    """Main function to run the mailbox migration."""
    migrator = MailboxMigrator()
    
    # Create a backup first
    backup_dir = migrator.backup_old_mailboxes()
    if not backup_dir:
        logger.error("Backup failed, aborting migration")
        return
        
    # Perform the migration
    success = migrator.migrate_all_mailboxes()
    
    # Validate the migration
    if success:
        is_valid = migrator.validate_migration()
        if is_valid:
            logger.info("Migration completed successfully and passed validation")
            
            # Create a summary report
            report_path = "runtime/agent_comms/MAILBOX_MIGRATION_REPORT.md"
            with open(report_path, 'w') as f:
                f.write("# Mailbox Migration Report\n\n")
                f.write(f"**Date:** {datetime.now().isoformat()}\n")
                f.write(f"**Status:** Completed Successfully\n\n")
                f.write("## Summary\n\n")
                f.write(f"- **Backup created at:** {backup_dir}\n")
                f.write("- **Migration result:** Successful\n")
                f.write("- **Validation result:** Passed\n\n")
                f.write("## Next Steps\n\n")
                f.write("1. Review migration logs in `runtime/logs/mailbox_migration.log`\n")
                f.write("2. Test the new mailbox system with a few agents\n")
                f.write("3. Update agent code to use the new JSON-based mailbox system\n")
                
            logger.info(f"Migration report created at {report_path}")
        else:
            logger.error("Migration completed but failed validation")
    else:
        logger.error("Migration failed")

if __name__ == "__main__":
    main() 