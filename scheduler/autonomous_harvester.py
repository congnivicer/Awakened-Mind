#!/usr/bin/env python3
"""
Autonomous Knowledge Harvesting Scheduler
Automatically runs various harvesting tasks at scheduled intervals
"""

import asyncio
import json
import schedule
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
import logging

@dataclass
class HarvestSchedule:
    """Configuration for a scheduled harvest"""
    id: str
    name: str
    harvest_type: str  # 'github', 'directory', 'web', etc.
    config: Dict  # Specific configuration for the harvest type
    schedule_type: str  # 'interval', 'daily', 'weekly', 'cron'
    schedule_config: Dict  # Timing configuration
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    error_count: int = 0

@dataclass
class HarvestResult:
    """Result of a harvest operation"""
    schedule_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = 'success'  # 'success', 'error', 'partial'
    documents_harvested: int = 0
    documents_stored: int = 0
    errors: Optional[List[str]] = None
    metadata: Optional[Dict] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}

class AutonomousHarvestScheduler:
    """
    Autonomous scheduler for knowledge harvesting operations
    Supports multiple harvest types and flexible scheduling
    """

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.schedules: Dict[str, HarvestSchedule] = {}
        self.harvest_history: List[HarvestResult] = []
        self.is_running = False
        self.scheduler_thread = None

        # Setup logging
        self.logger = self._setup_logging()

        # Load existing schedules
        self._load_schedules()

        # Harvest type handlers
        self.harvest_handlers = {
            'github': self._run_github_harvest,
            'directory': self._run_directory_harvest,
            'web': self._run_web_harvest
        }

    def _setup_logging(self):
        """Setup logging for the scheduler"""
        logger = logging.getLogger('AutonomousScheduler')
        logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if not logger.handlers:
            log_file = Path('/Volumes/Active_Mind/logs/autonomous_scheduler.log')
            log_file.parent.mkdir(parents=True, exist_ok=True)

            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            # Also log to console
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

    def _load_schedules(self):
        """Load existing harvest schedules from disk"""
        schedule_file = Path('/Volumes/Active_Mind/configs/harvest_schedules.json')

        if schedule_file.exists():
            try:
                with open(schedule_file, 'r') as f:
                    data = json.load(f)

                for schedule_data in data.get('schedules', []):
                    schedule = HarvestSchedule(**schedule_data)
                    self.schedules[schedule.id] = schedule

                self.logger.info(f"Loaded {len(self.schedules)} harvest schedules")

            except Exception as e:
                self.logger.error(f"Error loading schedules: {e}")

    def _save_schedules(self):
        """Save harvest schedules to disk"""
        schedule_file = Path('/Volumes/Active_Mind/configs/harvest_schedules.json')

        try:
            # Convert schedules to serializable format
            schedules_data = []
            for schedule in self.schedules.values():
                data = asdict(schedule)
                # Convert datetime objects to strings if needed
                last_run = data.get('last_run')
                if isinstance(last_run, datetime):
                    data['last_run'] = last_run.isoformat()
                elif last_run is not None and not isinstance(last_run, str):
                    data['last_run'] = str(last_run)

                next_run = data.get('next_run')
                if isinstance(next_run, datetime):
                    data['next_run'] = next_run.isoformat()
                elif next_run is not None and not isinstance(next_run, str):
                    data['next_run'] = str(next_run)
                schedules_data.append(data)

            schedule_file.parent.mkdir(parents=True, exist_ok=True)

            with open(schedule_file, 'w') as f:
                json.dump({
                    'last_updated': datetime.now().isoformat(),
                    'schedules': schedules_data
                }, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving schedules: {e}")

    def add_schedule(self, schedule: HarvestSchedule) -> bool:
        """
        Add a new harvest schedule

        Args:
            schedule: HarvestSchedule to add

        Returns:
            bool: True if added successfully
        """
        try:
            self.schedules[schedule.id] = schedule
            self._save_schedules()
            self._update_next_run(schedule)
            self.logger.info(f"Added harvest schedule: {schedule.name} ({schedule.id})")
            return True
        except Exception as e:
            self.logger.error(f"Error adding schedule: {e}")
            return False

    def remove_schedule(self, schedule_id: str) -> bool:
        """
        Remove a harvest schedule

        Args:
            schedule_id: ID of schedule to remove

        Returns:
            bool: True if removed successfully
        """
        try:
            if schedule_id in self.schedules:
                del self.schedules[schedule_id]
                self._save_schedules()
                self.logger.info(f"Removed harvest schedule: {schedule_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing schedule: {e}")
            return False

    def _update_next_run(self, schedule: HarvestSchedule):
        """Calculate and update the next run time for a schedule"""
        now = datetime.now()

        if schedule.schedule_type == 'interval':
            # Run every N minutes/hours
            interval_minutes = schedule.schedule_config.get('minutes', 60)
            schedule.next_run = now + timedelta(minutes=interval_minutes)

        elif schedule.schedule_type == 'daily':
            # Run daily at specific time
            hour = schedule.schedule_config.get('hour', 2)  # Default 2 AM
            minute = schedule.schedule_config.get('minute', 0)

            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)

            schedule.next_run = next_run

        elif schedule.schedule_type == 'weekly':
            # Run weekly on specific day and time
            day_of_week = schedule.schedule_config.get('day_of_week', 0)  # Monday
            hour = schedule.schedule_config.get('hour', 2)
            minute = schedule.schedule_config.get('minute', 0)

            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # Find next occurrence of target day
            days_ahead = (day_of_week - now.weekday()) % 7
            if days_ahead == 0 and next_run <= now:
                days_ahead = 7

            next_run += timedelta(days=days_ahead)
            schedule.next_run = next_run

    def start_scheduler(self):
        """Start the autonomous scheduler"""
        if self.is_running:
            self.logger.warning("Scheduler already running")
            return

        self.is_running = True
        self.logger.info("Starting autonomous harvest scheduler...")

        # Start the scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        # Schedule all enabled schedules
        for schedule in self.schedules.values():
            if schedule.enabled:
                self._schedule_harvest(schedule)

    def stop_scheduler(self):
        """Stop the autonomous scheduler"""
        self.is_running = False
        self.logger.info("Stopping autonomous harvest scheduler...")

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

    def _scheduler_loop(self):
        """Main scheduler loop running in background thread"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

                # Update next run times for all schedules
                self._update_all_next_runs()

            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)

    def _update_all_next_runs(self):
        """Update next run times for all schedules"""
        for schedule in self.schedules.values():
            if schedule.enabled and schedule.next_run:
                if datetime.now() >= schedule.next_run:
                    # Schedule is due, run it
                    asyncio.run(self._execute_harvest(schedule))

    def _schedule_harvest(self, harvest_schedule: HarvestSchedule):
        """Schedule a harvest using the schedule library"""
        def harvest_job():
            if self.is_running:
                asyncio.run(self._execute_harvest(harvest_schedule))

        if harvest_schedule.schedule_type == 'interval':
            minutes = harvest_schedule.schedule_config.get('minutes', 60)
            schedule.every(minutes).minutes.do(harvest_job)

        elif harvest_schedule.schedule_type == 'daily':
            hour = harvest_schedule.schedule_config.get('hour', 2)
            minute = harvest_schedule.schedule_config.get('minute', 0)
            try:
                hour = int(hour)
                minute = int(minute)
            except (TypeError, ValueError):
                raise ValueError(f"Invalid daily schedule configuration: {harvest_schedule.schedule_config}")

            schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(harvest_job)

        elif harvest_schedule.schedule_type == 'weekly':
            schedule.every().monday.do(harvest_job)  # Simplified for now

    async def _execute_harvest(self, schedule: HarvestSchedule) -> HarvestResult:
        """
        Execute a scheduled harvest

        Args:
            schedule: Schedule to execute

        Returns:
            HarvestResult with execution details
        """
        start_time = datetime.now()
        result = HarvestResult(
            schedule_id=schedule.id,
            start_time=start_time,
            status='success'
        )

        try:
            self.logger.info(f"Executing scheduled harvest: {schedule.name}")

            # Get the appropriate handler
            handler = self.harvest_handlers.get(schedule.harvest_type)
            if not handler:
                raise ValueError(f"No handler for harvest type: {schedule.harvest_type}")

            # Execute the harvest
            harvest_result = await handler(schedule)

            # Update result
            result.end_time = datetime.now()
            result.documents_harvested = harvest_result.get('documents_harvested', 0)
            result.documents_stored = harvest_result.get('documents_stored', 0)
            result.metadata = harvest_result

            # Update schedule statistics
            schedule.last_run = start_time
            schedule.run_count += 1
            schedule.success_count += 1
            self._update_next_run(schedule)

            self.logger.info(f"Harvest completed successfully: {schedule.name} - {result.documents_stored} documents stored")

        except Exception as e:
            result.status = 'error'
            result.end_time = datetime.now()
            if result.errors is not None:
                result.errors.append(str(e))

            # Update schedule statistics
            schedule.last_run = start_time
            schedule.run_count += 1
            schedule.error_count += 1

            self.logger.error(f"Harvest failed: {schedule.name} - {e}")

        finally:
            # Save updated schedule
            self._save_schedules()

            # Add to history (keep last 1000 results)
            self.harvest_history.append(result)
            if len(self.harvest_history) > 1000:
                self.harvest_history = self.harvest_history[-1000:]

            # Save history
            self._save_harvest_history()

        return result

    async def _run_github_harvest(self, schedule: HarvestSchedule) -> Dict:
        """Run a GitHub repository harvest"""
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not available for GitHub harvest")

        # Run the GitHub discovery pipeline
        result = await self.orchestrator.process_pipeline()

        return {
            'harvest_type': 'github',
            'repositories_discovered': result.get('summary', {}).get('repositories_discovered', 0),
            'documents_extracted': result.get('summary', {}).get('documents_extracted', 0),
            'documents_stored': result.get('summary', {}).get('documents_stored', 0),
            'status': result.get('status', 'unknown')
        }

    async def _run_directory_harvest(self, schedule: HarvestSchedule) -> Dict:
        """Run a manual directory harvest"""
        from ..scrapers.manual_directory_harvester import harvest_directory_for_orchestrator

        if not self.orchestrator:
            raise RuntimeError("Orchestrator not available for directory harvest")

        config = dict(schedule.config) if schedule.config else {}
        directory_path = config.pop('directory_path', None)
        if not directory_path:
            raise ValueError("No directory_path specified in schedule config")

        # Run the directory harvest
        result = await harvest_directory_for_orchestrator(
            self.orchestrator,
            directory_path,
            **config
        )

        return result

    async def _run_web_harvest(self, schedule: HarvestSchedule) -> Dict:
        """Run a web scraping harvest (placeholder for future implementation)"""
        # This would integrate with web scrapers
        return {
            'harvest_type': 'web',
            'documents_harvested': 0,
            'documents_stored': 0,
            'status': 'not_implemented'
        }

    def _save_harvest_history(self):
        """Save harvest history to disk"""
        history_file = Path('/Volumes/Active_Mind/logs/harvest_history.json')

        try:
            # Convert to serializable format
            history_data = []
            for result in self.harvest_history:
                data = asdict(result)
                data['start_time'] = data['start_time'].isoformat()
                data['end_time'] = data['end_time'].isoformat()
                history_data.append(data)

            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving harvest history: {e}")

    def get_schedule_status(self) -> Dict:
        """Get current status of all schedules"""
        return {
            'is_running': self.is_running,
            'total_schedules': len(self.schedules),
            'enabled_schedules': sum(1 for s in self.schedules.values() if s.enabled),
            'next_runs': {
                schedule_id: schedule.next_run.isoformat() if schedule.next_run else None
                for schedule_id, schedule in self.schedules.items()
                if schedule.enabled and schedule.next_run
            },
            'recent_results': len([r for r in self.harvest_history if r.end_time and r.end_time > datetime.now() - timedelta(hours=24)])
        }

    def create_sample_schedules(self):
        """Create some sample schedules for common use cases"""
        schedules = [
            HarvestSchedule(
                id='github_daily',
                name='Daily GitHub Discovery',
                harvest_type='github',
                config={},
                schedule_type='daily',
                schedule_config={'hour': 2, 'minute': 0},  # 2 AM daily
                enabled=True
            ),
            HarvestSchedule(
                id='docs_weekly',
                name='Weekly Documentation Harvest',
                harvest_type='directory',
                config={
                    'directory_path': '/Volumes/NHB_Workspace',
                    'file_patterns': ['*.md', '*.txt', '*.py'],
                    'recursive': True,
                    'max_depth': 3
                },
                schedule_type='weekly',
                schedule_config={'day_of_week': 0, 'hour': 3, 'minute': 0},  # Sunday 3 AM
                enabled=True
            ),
            HarvestSchedule(
                id='github_hourly',
                name='Hourly GitHub Check',
                harvest_type='github',
                config={'max_repos': 5},  # Smaller, more frequent runs
                schedule_type='interval',
                schedule_config={'minutes': 60},
                enabled=False  # Disabled by default to avoid rate limits
            )
        ]

        for schedule in schedules:
            self.add_schedule(schedule)

# Convenience functions for common operations
def create_github_schedule(name: str, interval_hours: int = 6) -> HarvestSchedule:
    """Create a GitHub harvesting schedule"""
    return HarvestSchedule(
        id=f"github_{name.lower().replace(' ', '_')}",
        name=name,
        harvest_type='github',
        config={},
        schedule_type='interval',
        schedule_config={'minutes': interval_hours * 60}
    )

def create_directory_schedule(name: str, directory_path: str, interval_hours: int = 24) -> HarvestSchedule:
    """Create a directory harvesting schedule"""
    return HarvestSchedule(
        id=f"dir_{name.lower().replace(' ', '_')}",
        name=name,
        harvest_type='directory',
        config={'directory_path': directory_path},
        schedule_type='interval',
        schedule_config={'minutes': interval_hours * 60}
    )

# Test function
async def test_autonomous_scheduler():
    """Test the autonomous scheduler"""
    print("🧪 Testing Autonomous Harvest Scheduler...")

    # Create scheduler instance
    scheduler = AutonomousHarvestScheduler()

    # Create sample schedules
    scheduler.create_sample_schedules()

    print(f"✅ Created {len(scheduler.schedules)} sample schedules")

    # Show status
    status = scheduler.get_schedule_status()
    print(f"📊 Status: {status}")

    # Show next runs
    print("\n📅 Next scheduled runs:")
    for schedule_id, next_run in status['next_runs'].items():
        if next_run:
            schedule = scheduler.schedules[schedule_id]
            print(f"  {schedule.name}: {next_run}")

    return scheduler

if __name__ == "__main__":
    # Run test
    scheduler = asyncio.run(test_autonomous_scheduler())
