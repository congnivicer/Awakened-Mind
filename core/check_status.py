#!/usr/bin/env python3
"""
Simple NHB Knowledge Infrastructure Status Checker
No external dependencies required - uses only Python standard library
"""

import json
from datetime import datetime
from pathlib import Path

def check_volumes():
    """Check if volumes are properly mounted"""
    print("📂 Volume Status:")
    volumes = {
        '/Volumes/Knowledge': 'Main knowledge storage',
        '/Volumes/Active_Mind': 'Processing and scrapers',
        '/Volumes/Memories': 'Persistent memory',
        '/Volumes/Archive': 'Historical data',
        '/Volumes/Little_Brain': 'Lightweight local cache'
    }
    
    all_mounted = True
    for volume, description in volumes.items():
        if Path(volume).exists():
            print(f"  ✅ {volume} - {description}")
        else:
            print(f"  ❌ {volume} - {description}")
            all_mounted = False
    
    return all_mounted

def check_components():
    """Check if key components exist"""
    print("\\n🧠 Component Status:")
    components = {
        '/Volumes/Little_Brain/mcp_orchestrator.py': 'Master Control Program (Fixed)',
        '/Volumes/Active_Mind/scrapers/universal_github_integration.py': 'GitHub Discovery System',
        '/Volumes/Active_Mind/scheduler/nightly_harvester.py': 'Nightly Automation',
        '/Volumes/Knowledge/chroma/chroma_init.py': 'ChromaDB System',
        '/Volumes/Little_Brain/requirements.txt': 'Dependencies List'
    }
    
    all_present = True
    for component, description in components.items():
        if Path(component).exists():
            # Get file size for context
            size = Path(component).stat().st_size
            print(f"  ✅ {description} ({size} bytes)")
        else:
            print(f"  ❌ {description} - Missing")
            all_present = False
    
    return all_present

def check_signals_and_logs():
    """Check for recent activity signals and logs"""
    print("\\n📡 Recent Activity:")
    
    # Check signals directory
    signals_dir = Path('/Volumes/Active_Mind/signals')
    if signals_dir.exists():
        signal_files = sorted(signals_dir.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
        print(f"  📊 {len(signal_files)} signal files found")
        
        for signal_file in signal_files[:3]:  # Show most recent 3
            try:
                with open(signal_file) as f:
                    data = json.load(f)
                timestamp = data.get('timestamp', 'unknown')
                status = data.get('status', 'unknown')
                print(f"    📄 {signal_file.name}: {status} at {timestamp}")
            except:
                print(f"    📄 {signal_file.name}: (unreadable)")
    else:
        print("  ❌ No signals directory found")
    
    # Check logs directory
    logs_dir = Path('/Volumes/Active_Mind/logs')
    if logs_dir.exists():
        log_files = list(logs_dir.glob('*.log'))
        print(f"  📋 {len(log_files)} log files found")
        
        # Check latest orchestrator log
        orch_log = logs_dir / 'orchestrator_activity.log'
        if orch_log.exists():
            size = orch_log.stat().st_size
            mod_time = datetime.fromtimestamp(orch_log.stat().st_mtime)
            print(f"    🤖 orchestrator_activity.log: {size} bytes, modified {mod_time}")
    else:
        print("  ❌ No logs directory found")

def check_knowledge_collections():
    """Check knowledge storage"""
    print("\\n💾 Knowledge Storage:")
    
    collections_dir = Path('/Volumes/Knowledge/collections')
    if collections_dir.exists():
        # Count JSON files (knowledge items)
        json_files = list(collections_dir.rglob('*.json'))
        print(f"  📚 {len(json_files)} knowledge items stored")
        
        # Check subdirectories
        subdirs = [d for d in collections_dir.iterdir() if d.is_dir()]
        for subdir in subdirs:
            count = len(list(subdir.glob('*.json')))
            print(f"    📁 {subdir.name}: {count} items")
    else:
        print("  ❌ Collections directory not found")
        print("    💡 This is normal for first-time setup")

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\\n📦 Dependency Status:")
    
    required_modules = [
        ('aiohttp', 'GitHub API calls'),
        ('schedule', 'Nightly automation'),
        ('chromadb', 'Vector database'),
        ('requests', 'HTTP requests')
    ]
    
    missing_deps = []
    
    for module, description in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module} - {description}")
        except ImportError:
            print(f"  ❌ {module} - {description} (MISSING)")
            missing_deps.append(module)
    
    if missing_deps:
        print(f"\\n  💡 Install missing dependencies with:")
        print(f"     pip3 install {' '.join(missing_deps)}")
        print(f"\\n  Or install all at once:")
        print(f"     pip3 install -r /Volumes/Little_Brain/requirements.txt")
    
    return len(missing_deps) == 0

def generate_summary():
    """Generate overall system readiness summary"""
    print("\\n" + "=" * 60)
    print("📋 NHB KNOWLEDGE INFRASTRUCTURE STATUS SUMMARY")
    print("=" * 60)
    
    volumes_ok = check_volumes()
    components_ok = check_components() 
    deps_ok = check_dependencies()
    
    check_signals_and_logs()
    check_knowledge_collections()
    
    print("\\n🎯 READINESS CHECK:")
    print(f"  Volumes Mounted: {'✅ Yes' if volumes_ok else '❌ No'}")
    print(f"  Components Built: {'✅ Yes' if components_ok else '❌ No'}")  
    print(f"  Dependencies: {'✅ Ready' if deps_ok else '❌ Install Needed'}")
    
    if volumes_ok and components_ok and deps_ok:
        print("\\n🚀 STATUS: SYSTEM READY FOR OPERATION!")
        print("\\n📝 Next steps:")
        print("   1. cd /Volumes/Little_Brain && python3 mcp_orchestrator.py")
        print("   2. cd /Volumes/Active_Mind/scheduler && python3 nightly_harvester.py --test")
    elif volumes_ok and components_ok:
        print("\\n⚠️  STATUS: SYSTEM BUILT, DEPENDENCIES NEEDED")
        print("\\n📝 Next step:")
        print("   pip3 install -r /Volumes/Little_Brain/requirements.txt")
    else:
        print("\\n❌ STATUS: SYSTEM INCOMPLETE")
        print("\\n📝 Issues to resolve:")
        if not volumes_ok:
            print("   - Mount missing volumes")
        if not components_ok:
            print("   - Rebuild missing components")

if __name__ == "__main__":
    generate_summary()