"""
Dynamic Instructions Manager
Allows updating instructions.txt via Telegram or Web UI with automatic backups.
MODULAR: Works independently, no imports from main.py or core modules.
"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict


class InstructionsManager:
    """
    Manages instructions.txt updates with versioning, validation, and backup system.
    Thread-safe for async operations.
    """

    def __init__(
        self,
        instructions_path: str = "instructions.txt",
        dynamic_path: str = "instructions_dynamic.txt",
        backup_dir: str = "instructions_backup"
    ):
        """
        Initialize the instructions manager.

        Args:
            instructions_path: Path to main instructions file
            dynamic_path: Path to dynamic instructions file (voice commands, etc)
            backup_dir: Directory to store automatic backups
        """
        self.instructions_path = Path(instructions_path)
        self.dynamic_path = Path(dynamic_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

        print(f"[INSTRUCTIONS] Manager initialized")
        print(f"  Instructions: {self.instructions_path}")
        print(f"  Dynamic: {self.dynamic_path}")
        print(f"  Backup dir: {self.backup_dir}")

    def get_current_instructions(self) -> str:
        """
        Read current main instructions file.

        Returns:
            Content of instructions.txt, or empty string if not found
        """
        if self.instructions_path.exists():
            try:
                return self.instructions_path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"[ERROR] Failed to read instructions: {e}")
                return ""
        return ""

    def get_dynamic_instructions(self) -> str:
        """
        Read dynamic instructions file (voice commands, rules added at runtime).

        Returns:
            Content of instructions_dynamic.txt, or empty string if not found
        """
        if self.dynamic_path.exists():
            try:
                return self.dynamic_path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"[ERROR] Failed to read dynamic instructions: {e}")
                return ""
        return ""

    async def update_instructions(
        self,
        new_content: str,
        mode: str = "replace",
        create_backup: bool = True
    ) -> Dict:
        """
        Update main instructions file with optional backup.

        Args:
            new_content: New instructions text
            mode: "replace" (default), "append", or "prepend"
            create_backup: Create timestamped backup before changes

        Returns:
            {
                "success": bool,
                "backup_path": str or None,
                "message": str,
                "mode": str
            }
        """
        try:
            # Validate content length
            if len(new_content.strip()) < 50:
                return {
                    "success": False,
                    "message": "Instructions too short (minimum 50 characters)",
                    "mode": mode
                }

            # Create backup if requested and file exists
            backup_path = None
            if create_backup and self.instructions_path.exists():
                backup_path = await self._create_backup(self.instructions_path)
                print(f"[INSTRUCTIONS] Backup created: {backup_path}")

            # Calculate final content based on mode
            if mode == "replace":
                final_content = new_content
            elif mode == "append":
                current = self.get_current_instructions()
                final_content = f"{current}\n\n{new_content}" if current else new_content
            elif mode == "prepend":
                current = self.get_current_instructions()
                final_content = f"{new_content}\n\n{current}" if current else new_content
            else:
                return {
                    "success": False,
                    "message": f"Invalid mode: {mode}. Use 'replace', 'append', or 'prepend'",
                    "mode": mode
                }

            # Write to file (async)
            await asyncio.to_thread(
                self.instructions_path.write_text,
                final_content,
                encoding='utf-8'
            )

            print(f"[INSTRUCTIONS] Updated ({mode} mode), {len(final_content)} chars")

            return {
                "success": True,
                "backup_path": str(backup_path) if backup_path else None,
                "message": f"Instructions updated successfully ({mode} mode)",
                "mode": mode
            }

        except Exception as e:
            print(f"[ERROR] Update failed: {e}")
            return {
                "success": False,
                "message": f"Update failed: {type(e).__name__}: {str(e)}",
                "mode": mode
            }

    async def update_dynamic_instructions(
        self,
        new_rule: str,
        create_backup: bool = True
    ) -> Dict:
        """
        Append to dynamic instructions file (new rules, voice commands).
        Automatically timestamps each entry.

        Args:
            new_rule: New rule or instruction to add
            create_backup: Create backup before changes

        Returns:
            {
                "success": bool,
                "backup_path": str or None,
                "message": str,
                "timestamp": str
            }
        """
        try:
            # Validate content
            if len(new_rule.strip()) < 10:
                return {
                    "success": False,
                    "message": "Rule too short (minimum 10 characters)",
                    "timestamp": None
                }

            # Create backup if requested and file exists
            backup_path = None
            if create_backup and self.dynamic_path.exists():
                backup_path = await self._create_backup(self.dynamic_path)
                print(f"[INSTRUCTIONS] Dynamic backup created: {backup_path}")

            # Read current content
            current = self.get_dynamic_instructions()

            # Create timestamped entry
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry = f"[{timestamp}] {new_rule}"
            new_content = f"{current}\n{entry}" if current else entry

            # Write to file (async)
            await asyncio.to_thread(
                self.dynamic_path.write_text,
                new_content,
                encoding='utf-8'
            )

            print(f"[INSTRUCTIONS] Dynamic rule added: {timestamp}")

            return {
                "success": True,
                "backup_path": str(backup_path) if backup_path else None,
                "message": f"Dynamic rule added at {timestamp}",
                "timestamp": timestamp
            }

        except Exception as e:
            print(f"[ERROR] Dynamic update failed: {e}")
            return {
                "success": False,
                "message": f"Dynamic update failed: {type(e).__name__}: {str(e)}",
                "timestamp": None
            }

    async def rollback_to_backup(self, backup_filename: str) -> Dict:
        """
        Restore instructions from a backup file.

        Args:
            backup_filename: Filename from instructions_backup/ directory

        Returns:
            {
                "success": bool,
                "message": str,
                "restored_timestamp": str or None
            }
        """
        try:
            backup_path = self.backup_dir / backup_filename

            if not backup_path.exists():
                return {
                    "success": False,
                    "message": f"Backup not found: {backup_filename}",
                    "restored_timestamp": None
                }

            # Read backup content
            content = await asyncio.to_thread(
                backup_path.read_text,
                encoding='utf-8'
            )

            # Create backup of current before restoring
            if self.instructions_path.exists():
                await self._create_backup(self.instructions_path)

            # Restore from backup
            await asyncio.to_thread(
                self.instructions_path.write_text,
                content,
                encoding='utf-8'
            )

            restored_time = backup_filename.split('_backup_')[-1].replace('.txt', '')
            print(f"[INSTRUCTIONS] Restored from backup: {backup_filename}")

            return {
                "success": True,
                "message": f"Restored from {backup_filename}",
                "restored_timestamp": restored_time
            }

        except Exception as e:
            print(f"[ERROR] Rollback failed: {e}")
            return {
                "success": False,
                "message": f"Rollback failed: {type(e).__name__}: {str(e)}",
                "restored_timestamp": None
            }

    async def _create_backup(self, source_path: Optional[Path] = None) -> Path:
        """
        Create timestamped backup of instructions file.

        Args:
            source_path: File to backup (default: main instructions)

        Returns:
            Path to created backup file
        """
        source = source_path or self.instructions_path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{source.stem}_backup_{timestamp}{source.suffix}"
        backup_path = self.backup_dir / backup_name

        # Read source and write to backup (async)
        content = await asyncio.to_thread(source.read_text, encoding='utf-8')
        await asyncio.to_thread(backup_path.write_text, content, encoding='utf-8')

        return backup_path

    def list_backups(self, limit: int = 10) -> list:
        """
        List available backup files, most recent first.

        Args:
            limit: Maximum number of backups to return

        Returns:
            List of backup filenames (most recent first)
        """
        backups = sorted(
            [f.name for f in self.backup_dir.glob("instructions_backup_*.txt")],
            reverse=True
        )
        return backups[:limit]

    def get_stats(self) -> Dict:
        """
        Get statistics about instructions and backups.

        Returns:
            {
                "instructions_size": int (chars),
                "dynamic_size": int (chars),
                "backup_count": int,
                "latest_backup": str or None,
                "instructions_exists": bool
            }
        """
        instructions_content = self.get_current_instructions()
        dynamic_content = self.get_dynamic_instructions()
        backups = self.list_backups(limit=1)

        return {
            "instructions_size": len(instructions_content),
            "dynamic_size": len(dynamic_content),
            "backup_count": len(list(self.backup_dir.glob("instructions_backup_*.txt"))),
            "latest_backup": backups[0] if backups else None,
            "instructions_exists": self.instructions_path.exists(),
            "dynamic_exists": self.dynamic_path.exists()
        }

    async def export_to_dict(self) -> Dict:
        """
        Export all instructions and metadata for API/web responses.

        Returns:
            {
                "core": str,
                "dynamic": str,
                "backup_count": int,
                "last_modified": str,
                "sizes": {core_chars, dynamic_chars}
            }
        """
        core = self.get_current_instructions()
        dynamic = self.get_dynamic_instructions()

        last_modified = None
        if self.instructions_path.exists():
            stat = await asyncio.to_thread(self.instructions_path.stat)
            last_modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

        return {
            "core": core,
            "dynamic": dynamic,
            "backup_count": len(list(self.backup_dir.glob("instructions_backup_*.txt"))),
            "last_modified": last_modified,
            "sizes": {
                "core_chars": len(core),
                "dynamic_chars": len(dynamic)
            }
        }


# Singleton instance for use across the application
_instructions_manager: Optional[InstructionsManager] = None


def get_instructions_manager() -> InstructionsManager:
    """Get or create singleton instance of InstructionsManager."""
    global _instructions_manager
    if _instructions_manager is None:
        _instructions_manager = InstructionsManager()
    return _instructions_manager
