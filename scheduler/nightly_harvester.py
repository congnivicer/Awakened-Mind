#!/usr/bin/env python3
"""
Nightly Knowledge Harvesting Scheduler
Runs the complete pipeline automatically at scheduled intervals

This scheduler coordinates the complete knowledge harvesting workflow:
1. Activate VPN rotation for anonymity
2. Run repository discovery
3. Extract and process content
4. Store in ChromaDB collections
5. Generate reports and signals
"""

import schedule
import time
import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path

# Add the Little_Brain volume to the path for the orchestrator
sys.path.append('/Volumes/Little_Brain')

async def run_harvest():
    """Run the complete harvest pipeline"""
    start_time = datetime.now()
    print(f"🌙 Starting nightly knowledge harvest at {start_time.strftime('%Y-%m-%d %H:%M:%S')}...")
    
    try:
        # Import the orchestrator (with fallback if dependencies not available)
        try:
            from mcp_orchestrator import MCPKnowledgeOrchestrator
            orchestrator = MCPKnowledgeOrchestrator()
            
            # Initialize components
            success = await orchestrator.initialize_components()
            if not success:
                print("❌ Failed to initialize orchestrator components")
                return
            
            # Run the full pipeline
            results = await orchestrator.process_pipeline()
            
            # Report results
            if results['status'] == 'success' and 'summary' in results:
                summary = results['summary']
                print(f"✅ Harvest completed successfully!")
                print(f"📊 Repositories discovered: {summary.get('repositories_discovered', 0)}")
                print(f"📄 Documents extracted: {summary.get('documents_extracted', 0)}")
                print(f"💾 Documents stored: {summary.get('documents_stored', 0)}")
                print(f"📈 Total knowledge items: {summary.get('total_knowledge_items', 0)}")
            else:
                print(f"⚠️ Harvest completed with status: {results['status']}")
                if 'error' in results:
                    print(f"Error: {results['error']}")
                    
        except ImportError as e:
            print(f"❌ Cannot import orchestrator: {e}")
            print("💡 Running basic discovery mode...")
            await run_basic_discovery()
            
    except Exception as e:
        print(f"❌ Harvest failed: {e}")
        
        # Log the error
        error_log = {
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'type': 'harvest_failure'
        }
        
        log_dir = Path('/Volumes/Active_Mind/logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / 'harvest_errors.log', 'a') as f:
            f.write(json.dumps(error_log) + '\n')
    
    duration = datetime.now() - start_time
    print(f"⏱️ Harvest duration: {duration}")

async def run_basic_discovery():
    """Fallback discovery mode when full orchestrator isn't available"""
    print("🔍 Running basic repository discovery...")
    
    try:
        # Create a basic discovery report without full orchestrator
        discovery_report = {
            'timestamp': datetime.now().isoformat(),
            'mode': 'basic_fallback',
            'status': 'completed',
            'repositories_queued': 'pending_full_system',
            'note': 'Waiting for dependencies to be installed'
        }
        
        # Save to signals directory
        signals_dir = Path('/Volumes/Active_Mind/signals')
        signals_dir.mkdir(parents=True, exist_ok=True)
        
        with open(signals_dir / 'basic_discovery_report.json', 'w') as f:
            json.dump(discovery_report, f, indent=2)
        
        print("📝 Basic discovery report saved to signals directory")
        
    except Exception as e:
        print(f"❌ Basic discovery failed: {e}")

def schedule_harvests():
    """Schedule nightly runs and testing cycles"""
    
    print("📅 Setting up knowledge harvest scheduler...")
    
    # Main nightly harvest at 2 AM
    schedule.every().day.at("02:00").do(lambda: asyncio.run(run_harvest()))
    print("🌙 Nightly harvest scheduled for 2:00 AM")
    
    # Additional harvest every 6 hours for active development/testing
    schedule.every(6).hours.do(lambda: asyncio.run(run_harvest()))
    print("🔄 Development harvests scheduled every 6 hours")
    
    # Light discovery check every 2 hours (less intensive)
    schedule.every(2).hours.do(lambda: asyncio.run(run_basic_discovery()))
    print("🔍 Light discovery checks scheduled every 2 hours")
    
    print("📊 Scheduler status:")
    print(f"  Next nightly harvest: {schedule.next_run()}")
    print(f"  Total jobs scheduled: {len(schedule.get_jobs())}")
    print("")
    
    # Save scheduler status
    scheduler_status = {
        'initialized': datetime.now().isoformat(),
        'next_run': str(schedule.next_run()),
        'jobs_count': len(schedule.get_jobs()),
        'jobs': [
            {
                'job': str(job.job_func),
                'interval': str(job.interval),
                'next_run': str(job.next_run)
            } for job in schedule.get_jobs()
        ]
    }
    
    status_dir = Path('/Volumes/Active_Mind/signals')
    status_dir.mkdir(parents=True, exist_ok=True)
    with open(status_dir / 'scheduler_status.json', 'w') as f:
        json.dump(scheduler_status, f, indent=2)
    
    print("⏳ Scheduler started. Waiting for scheduled runs...")
    print("   (Press Ctrl+C to stop the scheduler)")
    
    # Main scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n👋 Scheduler stopped by user")
    except Exception as e:
        print(f"\n❌ Scheduler error: {e}")
        print("Restarting scheduler in 5 minutes...")
        time.sleep(300)
        schedule_harvests()  # Recursive restart

def run_immediate_test():
    """Run an immediate test harvest (for development/testing)"""
    print("🧪 Running immediate test harvest...")
    asyncio.run(run_harvest())

def main():
    """Main entry point with command line options"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NHB Knowledge Harvesting Scheduler')
    parser.add_argument('--test', action='store_true', help='Run immediate test harvest')
    parser.add_argument('--schedule', action='store_true', help='Start the scheduler')
    parser.add_argument('--status', action='store_true', help='Show scheduler status')
    
    args = parser.parse_args()
    
    if args.test:
        run_immediate_test()
    elif args.status:
        show_scheduler_status()
    elif args.schedule:
        schedule_harvests()
    else:
        print("NHB Knowledge Harvesting Scheduler")
        print("Usage:")
        print("  --test      Run immediate test harvest")
        print("  --schedule  Start the nightly scheduler")
        print("  --status    Show current status")
        print("")
        print("Starting default mode: immediate test...")
        run_immediate_test()

def show_scheduler_status():
    """Show current scheduler and system status"""
    print("📊 NHB Knowledge Harvesting System Status")
    print("=" * 50)
    
    # Check if volumes are mounted
    volumes = ['/Volumes/Knowledge', '/Volumes/Active_Mind', '/Volumes/Memories', '/Volumes/Archive', '/Volumes/Little_Brain']
    for volume in volumes:
        status = "✅ Mounted" if Path(volume).exists() else "❌ Not mounted"
        print(f"  {volume}: {status}")
    
    print("")
    
    # Check for orchestrator
    orchestrator_path = Path('/Volumes/Little_Brain/mcp_orchestrator.py')
    orchestrator_status = "✅ Available" if orchestrator_path.exists() else "❌ Missing"
    print(f"  MCP Orchestrator: {orchestrator_status}")
    
    # Check for GitHub integration
    github_path = Path('/Volumes/Active_Mind/scrapers/universal_github_integration.py')
    github_status = "✅ Available" if github_path.exists() else "❌ Missing"
    print(f"  GitHub Integration: {github_status}")
    
    print("")
    
    # Check latest signals
    signals_dir = Path('/Volumes/Active_Mind/signals')
    if signals_dir.exists():
        signal_files = list(signals_dir.glob('*.json'))
        print(f"  Signal files: {len(signal_files)}")
        for signal_file in signal_files[-3:]:  # Show last 3
            try:
                with open(signal_file) as f:
                    data = json.load(f)
                timestamp = data.get('timestamp', 'unknown')
                print(f"    {signal_file.name}: {timestamp}")
            except:
                print(f"    {signal_file.name}: (unreadable)")
    else:
        print("  Signals directory: ❌ Not found")
    
    print("")
    
    # Check knowledge collections
    collections_dir = Path('/Volumes/Knowledge/collections')
    if collections_dir.exists():
        json_files = list(collections_dir.rglob('*.json'))
        print(f"  Knowledge items: {len(json_files)}")
    else:
        print("  Knowledge collections: ❌ Not found")

if __name__ == "__main__":
    main()