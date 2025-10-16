#!/usr/bin/env python3
"""
Comprehensive Harvest System Test
Tests all components of the knowledge harvesting system end-to-end
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add the project root to Python path
sys.path.append('/Volumes/NHB_Workspace')

from awakened_mind.core.mcp_orchestrator import MCPKnowledgeOrchestrator
from awakened_mind.scrapers.manual_directory_harvester import ManualDirectoryHarvester, DirectoryHarvestConfig
from awakened_mind.scheduler.autonomous_harvester import AutonomousHarvestScheduler

class HarvestSystemTester:
    """Comprehensive tester for the entire harvest system"""

    def __init__(self):
        self.results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }
        self.orchestrator = None
        self.harvester = None
        self.scheduler = None

    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log a test result"""
        self.results['total_tests'] += 1
        if passed:
            self.results['passed_tests'] += 1
            status = "✅ PASS"
        else:
            self.results['failed_tests'] += 1
            status = "❌ FAIL"

        result = {
            'test_name': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }

        self.results['test_details'].append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"      {details}")

    async def test_orchestrator_initialization(self):
        """Test MCP Orchestrator initialization"""
        print("\n🧪 Testing MCP Orchestrator Initialization...")

        try:
            self.orchestrator = MCPKnowledgeOrchestrator()

            # Test basic initialization
            assert self.orchestrator.status is not None
            assert self.orchestrator.knowledge_system is None  # Should be None initially
            assert self.orchestrator.github_discoverer is None  # Should be None initially

            self.log_test_result(
                "Orchestrator basic initialization",
                True,
                "Orchestrator initialized with correct initial state"
            )

            # Test component initialization
            success = await self.orchestrator.initialize_components()
            if success:
                self.log_test_result(
                    "Orchestrator component initialization",
                    True,
                    "All components initialized successfully"
                )
            else:
                self.log_test_result(
                    "Orchestrator component initialization",
                    False,
                    "Component initialization failed"
                )

        except Exception as e:
            self.log_test_result(
                "Orchestrator initialization",
                False,
                f"Exception during initialization: {e}"
            )

    async def test_manual_directory_harvester(self):
        """Test manual directory harvesting"""
        print("\n🧪 Testing Manual Directory Harvester...")

        try:
            # Create harvester instance
            self.harvester = ManualDirectoryHarvester()

            # Test configuration
            config = DirectoryHarvestConfig(
                source_path="/Volumes/NHB_Workspace/awakened_mind",
                recursive=True,
                max_depth=2,
                file_patterns=['*.md', '*.py', '*.txt'],
                min_file_size=50
            )

            # Test directory validation
            assert Path(config.source_path).exists(), "Test directory should exist"

            self.log_test_result(
                "Directory harvester configuration",
                True,
                "Configuration created and validated successfully"
            )

            # Test harvesting
            documents = await self.harvester.harvest_directory(config)

            # Validate results
            assert len(documents) > 0, "Should harvest at least some documents"

            # Check document structure
            for doc in documents[:3]:  # Check first 3 documents
                assert hasattr(doc, 'id'), "Document should have ID"
                assert hasattr(doc, 'title'), "Document should have title"
                assert hasattr(doc, 'content'), "Document should have content"
                assert hasattr(doc, 'file_type'), "Document should have file_type"
                assert len(doc.content) > 0, "Document content should not be empty"

            stats = self.harvester.get_stats()

            self.log_test_result(
                "Directory harvesting execution",
                True,
                f"Harvested {len(documents)} documents, processed {stats['files_processed']} files"
            )

            # Test sample documents
            sample_docs = documents[:3]
            for doc in sample_docs:
                print(f"    📄 {doc.title} ({doc.file_type}, {doc.size} bytes)")

        except Exception as e:
            self.log_test_result(
                "Manual directory harvesting",
                False,
                f"Exception during harvesting: {e}"
            )

    async def test_autonomous_scheduler(self):
        """Test autonomous scheduler"""
        print("\n🧪 Testing Autonomous Scheduler...")

        try:
            # Create scheduler without orchestrator for testing
            self.scheduler = AutonomousHarvestScheduler()

            # Test schedule creation
            self.scheduler.create_sample_schedules()

            assert len(self.scheduler.schedules) > 0, "Should create sample schedules"

            self.log_test_result(
                "Scheduler schedule creation",
                True,
                f"Created {len(self.scheduler.schedules)} sample schedules"
            )

            # Test schedule status
            status = self.scheduler.get_schedule_status()

            assert 'total_schedules' in status
            assert 'enabled_schedules' in status
            assert status['total_schedules'] > 0

            self.log_test_result(
                "Scheduler status reporting",
                True,
                f"Status: {status['total_schedules']} total, {status['enabled_schedules']} enabled"
            )

            # Test schedule persistence (save/load)
            initial_count = len(self.scheduler.schedules)

            # Create a new schedule
            from awakened_mind.scheduler.autonomous_harvester import HarvestSchedule
            test_schedule = HarvestSchedule(
                id='test_schedule',
                name='Test Schedule',
                harvest_type='directory',
                config={'directory_path': '/tmp'},
                schedule_type='interval',
                schedule_config={'minutes': 60}
            )

            self.scheduler.add_schedule(test_schedule)
            assert len(self.scheduler.schedules) == initial_count + 1

            # Create new scheduler instance to test loading
            new_scheduler = AutonomousHarvestScheduler()
            assert len(new_scheduler.schedules) > 0, "Schedules should persist"

            self.log_test_result(
                "Schedule persistence",
                True,
                "Schedules saved and loaded correctly"
            )

        except Exception as e:
            self.log_test_result(
                "Autonomous scheduler",
                False,
                f"Exception during scheduler testing: {e}"
            )

    async def test_end_to_end_integration(self):
        """Test full end-to-end integration"""
        print("\n🧪 Testing End-to-End Integration...")

        try:
            # Initialize orchestrator with components
            self.orchestrator = MCPKnowledgeOrchestrator()
            await self.orchestrator.initialize_components()

            # Test directory harvesting with orchestrator
            from awakened_mind.scrapers.manual_directory_harvester import harvest_directory_for_orchestrator

            result = await harvest_directory_for_orchestrator(
                self.orchestrator,
                "/Volumes/NHB_Workspace/awakened_mind",
                recursive=True,
                max_depth=2,
                file_patterns=['*.md', '*.py'],
                min_file_size=50
            )

            # Validate integration results
            assert result['status'] == 'completed', "Integration should complete successfully"
            assert result['documents_harvested'] > 0, "Should harvest documents through orchestrator"
            assert 'stats' in result, "Should include statistics"

            self.log_test_result(
                "End-to-end integration",
                True,
                f"Integration successful: {result['documents_harvested']} harvested, {result['documents_stored']} stored"
            )

            # Test scheduler with orchestrator
            scheduler = AutonomousHarvestScheduler(self.orchestrator)

            # Test that scheduler can access orchestrator
            assert scheduler.orchestrator == self.orchestrator

            self.log_test_result(
                "Scheduler-orchestrator integration",
                True,
                "Scheduler properly connected to orchestrator"
            )

        except Exception as e:
            self.log_test_result(
                "End-to-end integration",
                False,
                f"Exception during integration testing: {e}"
            )

    async def test_system_health_check(self):
        """Test system health and monitoring"""
        print("\n🧪 Testing System Health Check...")

        try:
            if self.orchestrator:
                # Test orchestrator health check
                health = await self.orchestrator.health_check()

                assert 'timestamp' in health
                assert 'overall_status' in health
                assert 'components' in health
                assert 'metrics' in health

                self.log_test_result(
                    "Orchestrator health check",
                    True,
                    f"Health status: {health['overall_status']}, knowledge items: {health['metrics']['knowledge_items']}"
                )

            if self.scheduler:
                # Test scheduler status
                status = self.scheduler.get_schedule_status()

                assert 'is_running' in status
                assert 'total_schedules' in status

                self.log_test_result(
                    "Scheduler status check",
                    True,
                    f"Scheduler status: {status['total_schedules']} schedules, {status['enabled_schedules']} enabled"
                )

        except Exception as e:
            self.log_test_result(
                "System health check",
                False,
                f"Exception during health check: {e}"
            )

    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Comprehensive Harvest System Tests")
        print("=" * 60)

        # Run individual test suites
        await self.test_orchestrator_initialization()
        await self.test_manual_directory_harvester()
        await self.test_autonomous_scheduler()
        await self.test_end_to_end_integration()
        await self.test_system_health_check()

        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"Passed: {self.results['passed_tests']}")
        print(f"Failed: {self.results['failed_tests']}")

        success_rate = (self.results['passed_tests'] / self.results['total_tests']) * 100 if self.results['total_tests'] > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")

        if self.results['failed_tests'] == 0:
            print("\n🎉 ALL TESTS PASSED! System is ready for production use.")
        elif success_rate >= 80:
            print("\n⚠️  MOST TESTS PASSED! System is functional but needs some fixes.")
        else:
            print("\n❌ SIGNIFICANT ISSUES FOUND! System needs fixes before production use.")

        # Save detailed results
        self._save_test_results()

        return self.results['failed_tests'] == 0

    def _save_test_results(self):
        """Save detailed test results to file"""
        try:
            results_file = Path('/Volumes/Active_Mind/logs/comprehensive_test_results.json')
            results_file.parent.mkdir(parents=True, exist_ok=True)

            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2)

            print(f"\n📋 Detailed results saved to: {results_file}")

        except Exception as e:
            print(f"Warning: Could not save test results: {e}")

# Convenience function to run tests
async def run_comprehensive_tests():
    """Run all comprehensive tests"""
    tester = HarvestSystemTester()
    success = await tester.run_all_tests()
    return success

# Individual test functions for selective testing
async def test_directory_harvester_only():
    """Test only the directory harvester"""
    print("🧪 Testing Directory Harvester Only...")

    harvester = ManualDirectoryHarvester()
    config = DirectoryHarvestConfig(
        source_path="/Volumes/NHB_Workspace/awakened_mind",
        recursive=True,
        max_depth=2,
        file_patterns=['*.md', '*.py', '*.txt'],
        min_file_size=50
    )

    documents = await harvester.harvest_directory(config)
    print(f"✅ Harvested {len(documents)} documents")
    print(f"📊 Stats: {harvester.get_stats()}")

    return len(documents) > 0

async def test_scheduler_only():
    """Test only the scheduler"""
    print("🧪 Testing Scheduler Only...")

    scheduler = AutonomousHarvestScheduler()
    scheduler.create_sample_schedules()

    status = scheduler.get_schedule_status()
    print(f"✅ Created {status['total_schedules']} schedules")
    print(f"📊 Status: {status}")

    return status['total_schedules'] > 0

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Comprehensive Harvest System Test')
    parser.add_argument('--test', choices=['all', 'directory', 'scheduler', 'integration'],
                       default='all', help='Test component to run')

    args = parser.parse_args()

    if args.test == 'all':
        success = asyncio.run(run_comprehensive_tests())
        exit(0 if success else 1)
    elif args.test == 'directory':
        success = asyncio.run(test_directory_harvester_only())
        exit(0 if success else 1)
    elif args.test == 'scheduler':
        success = asyncio.run(test_scheduler_only())
        exit(0 if success else 1)
    elif args.test == 'integration':
        # Run integration test
        tester = HarvestSystemTester()
        success = asyncio.run(tester.test_end_to_end_integration())
        exit(0 if success else 1)
