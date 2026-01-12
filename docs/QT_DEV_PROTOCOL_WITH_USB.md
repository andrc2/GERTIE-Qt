# GERTIE Qt Development Protocol
# With Automatic USB Sync
# Updated: 2026-01-12

## IMMUTABLE CONFIGURATION

**Qt Project**: `/Users/andrew1/Desktop/GERTIE_WORKSPACE/01_ACTIVE_PROJECTS/camera_system_qt_conversion`
**USB Mount**: `/Volumes/NO NAME/`
**Session Log**: `/Users/andrew1/Desktop/GERTIE_SESSION_LOG.md`

---

## PHASE 0: INITIALIZATION (Always First)

### 0.1 Read Session Log
```
DC: read_file path="/Users/andrew1/Desktop/GERTIE_SESSION_LOG.md" offset=-200 length=200
```

### 0.2 Check Git Status
```
DC: start_process command="cd ~/Desktop/GERTIE_WORKSPACE/01_ACTIVE_PROJECTS/camera_system_qt_conversion && git status -s && git log -1 --oneline" timeout_ms=3000
```

### 0.3 Check USB Mounted
```
DC: start_process command="ls -la /Volumes/NO\ NAME/ 2>/dev/null && echo '✅ USB mounted' || echo '⚠️ USB NOT MOUNTED - attach before fixes'" timeout_ms=2000
```

### 0.4 Log Session Start
```
DC: write_file path="/Users/andrew1/Desktop/GERTIE_SESSION_LOG.md" mode="append" content="
---
## SESSION: [DATE TIME]
**Issue**: [USER REQUEST]
**USB**: [MOUNTED/NOT MOUNTED]
"
```

---

## PHASE 3: APPLY FIX (With Automatic USB Sync)

### 3.1 Make Edit
```
DC: edit_block file_path="/Users/andrew1/Desktop/GERTIE_WORKSPACE/01_ACTIVE_PROJECTS/camera_system_qt_conversion/src/[FILE]" old_string="[EXACT_OLD]" new_string="[EXACT_NEW]" expected_replacements=1
```

### 3.2 Verify Edit
```
DC: start_process command="grep -n '[PATTERN]' ~/Desktop/GERTIE_WORKSPACE/01_ACTIVE_PROJECTS/camera_system_qt_conversion/src/[FILE]" timeout_ms=2000
```

### 3.3 Syntax Check
```
DC: start_process command="cd ~/Desktop/GERTIE_WORKSPACE/01_ACTIVE_PROJECTS/camera_system_qt_conversion && python3 -m py_compile src/[FILE] && echo '✅ Syntax OK'" timeout_ms=3000
```

### 3.4 Commit
```
DC: start_process command="cd ~/Desktop/GERTIE_WORKSPACE/01_ACTIVE_PROJECTS/camera_system_qt_conversion && git add src/[FILE] && git commit -m 'Fix: [DESCRIPTION]'" timeout_ms=5000
```

### 3.5 ⭐ AUTO-SYNC TO USB (MANDATORY)
```
DC: start_process command="rm -rf /Volumes/NO\ NAME/camera_system_qt_conversion && cp -r ~/Desktop/GERTIE_WORKSPACE/01_ACTIVE_PROJECTS/camera_system_qt_conversion /Volumes/NO\ NAME/ && echo '✅ USB SYNCED'" timeout_ms=30000
```

### 3.6 Verify Fix on USB
```
DC: start_process command="grep '[FIX_PATTERN]' /Volumes/NO\ NAME/camera_system_qt_conversion/src/[FILE] && echo '✅ Fix confirmed on USB'" timeout_ms=3000
```

### 3.7 Log Fix
```
DC: write_file path="/Users/andrew1/Desktop/GERTIE_SESSION_LOG.md" mode="append" content="
- [TIME] Fix Applied:
  - File: [PATH]
  - Change: [DESCRIPTION]
  - Commit: [HASH]
  - USB: ✅ Synced
"
```

---

## PHASE 5: DEPLOYMENT PREP

### 5.1 Update DEPLOY_NOW.txt on USB
```
DC: write_file path="/Volumes/NO NAME/DEPLOY_NOW.txt" mode="rewrite" content="[INSTRUCTIONS]"
```

### 5.2 Final USB Verification
```
DC: start_process command="ls -la /Volumes/NO\ NAME/ && git -C /Volumes/NO\ NAME/camera_system_qt_conversion log -1 --oneline" timeout_ms=5000
```

---

## ENFORCEMENT RULES

### ALWAYS (Qt Development):
- Check USB mounted before making fixes
- Sync to USB immediately after every commit
- Verify fix exists on USB before marking complete
- Update DEPLOY_NOW.txt with current fix summary

### NEVER:
- Commit without syncing to USB
- Mark fix complete without USB verification
- Proceed if USB not mounted (warn user first)

---

## QUICK REFERENCE

### Single Fix Workflow:
1. Edit file
2. Verify edit (grep)
3. Syntax check (py_compile)
4. Commit (git)
5. **Sync USB** (rm + cp)
6. **Verify USB** (grep on USB path)
7. Log

### USB Sync Command (Copy-Paste):
```bash
rm -rf /Volumes/NO\ NAME/camera_system_qt_conversion && cp -r ~/Desktop/GERTIE_WORKSPACE/01_ACTIVE_PROJECTS/camera_system_qt_conversion /Volumes/NO\ NAME/ && echo "✅ USB SYNCED"
```

