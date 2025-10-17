# 🎯 AWAKENED MIND - IMMEDIATE ACTION PLAN

## Step 1: Run Validation (2 min)
```bash
cd /Volumes/NHB_Workspace
chmod +x validate_awakened_mind.sh
./validate_awakened_mind.sh
```

## Step 2: Fix Critical Bug (5 min)
```bash
# Open the file
vim /Volumes/NHB_Workspace/awakened_mind/core/mcp_orchestrator.py

# Go to line 156 and change:
# FROM: if not await self.initialize_components():
# TO:   if self.knowledge_system is None or self.github_discoverer is None:
#           if not await self.initialize_components():
```

## Step 3: Extract K9 Product (10 min)
```bash
cd /Volumes/NHB_Workspace/k9-cadet-workspace

# Find product files
find . -name "*.py" -path "*/api/*" -o -path "*/services/*" -o -path "*/core/*"

# Extract them
mkdir -p ../k9-product-extracted
cp -r [found_directories] ../k9-product-extracted/
```

## Step 4: Test Components (10 min)
```bash
# Test awakened_mind
cd /Volumes/NHB_Workspace/awakened_mind
python -m pytest tests/

# Test cosmos  
cd /Volumes/NHB_Workspace/cosmos
python -m pytest tests/

# Test extracted k9
cd /Volumes/NHB_Workspace/k9-product-extracted
python main.py --test
```

## Step 5: Stage Integration (15 min)
```bash
# Create staging area
mkdir -p /Volumes/NHB_Workspace/staging/integrated/{core,modules,services,config}

# Copy components
cp -r /Volumes/NHB_Workspace/awakened_mind/* /Volumes/NHB_Workspace/staging/integrated/core/
cp -r /Volumes/NHB_Workspace/cosmos/* /Volumes/NHB_Workspace/staging/integrated/modules/
cp -r /Volumes/NHB_Workspace/k9-product-extracted/* /Volumes/NHB_Workspace/staging/integrated/services/

# Test integration
cd /Volumes/NHB_Workspace/staging/integrated
python -c "import core; import modules; import services; print('✅ Integration successful')"
```

## Step 6: Deploy to Complete (5 min)
```bash
# ONLY if all tests pass!

# Backup existing
tar -czf ~/complete_backup_$(date +%Y%m%d).tar.gz /Volumes/NHB_Workspace/Awakened-Mind-Complete/

# Deploy
cp -r /Volumes/NHB_Workspace/staging/integrated/* /Volumes/NHB_Workspace/Awakened-Mind-Complete/

# Lock it
echo "DEPLOYED: $(date)" > /Volumes/NHB_Workspace/Awakened-Mind-Complete/.LOCKED
```

## ⏱️ Total Time: ~45 minutes

## ✅ Success Checklist
- [ ] Validation script runs clean
- [ ] Double init bug fixed
- [ ] K9 product extracted
- [ ] All tests pass
- [ ] Integration tested in staging
- [ ] Deployed to Complete
- [ ] Complete directory locked

## 🚨 If Something Breaks
1. STOP immediately
2. Restore from backup
3. Document what happened
4. Try again with smaller steps

## 📝 For Next AI Assistant
Leave clear notes:
- What you completed: _______
- What's in progress: _______
- Any blockers: _______
- Your branch name: _______
