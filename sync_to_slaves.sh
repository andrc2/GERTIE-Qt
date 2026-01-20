#!/bin/bash
# GERTIE Qt - Smart Deployment Script
# Only syncs/restarts when necessary, checks service status first
# Logs to /home/andrc1/Desktop/updatelog.txt

set -e  # Exit on error

# Configuration
LOG_FILE="/home/andrc1/Desktop/updatelog.txt"
REMOTE_USER="andrc1"
REMOTE_SLAVES=(
    "192.168.0.201"  # rep1
    "192.168.0.202"  # rep2
    "192.168.0.203"  # rep3
    "192.168.0.204"  # rep4
    "192.168.0.205"  # rep5
    "192.168.0.206"  # rep6
    "192.168.0.207"  # rep7
)
SOURCE_DIR="/home/andrc1/camera_system_qt_conversion"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Counters for summary
SLAVES_SYNCED=0
SLAVES_SKIPPED=0
SLAVES_FAILED=0
SERVICES_RESTARTED=0

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$ts] [$level] $message" | tee -a "$LOG_FILE"
}

log_section() {
    local section="$1"
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $section" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
}

# Get local git commit hash
get_local_commit() {
    if [ -d "$SOURCE_DIR/.git" ]; then
        cd "$SOURCE_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown"
    else
        # Use checksum of key files as fallback
        md5sum "$SOURCE_DIR/slave/video_stream.py" "$SOURCE_DIR/slave/still_capture.py" 2>/dev/null | md5sum | cut -d' ' -f1 | cut -c1-8
    fi
}

# Get remote file checksum
get_remote_checksum() {
    local ip=$1
    ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "md5sum $SOURCE_DIR/slave/video_stream.py $SOURCE_DIR/slave/still_capture.py 2>/dev/null | md5sum | cut -d' ' -f1 | cut -c1-8" 2>/dev/null || echo "none"
}

# Check if Qt services are installed and running on remote slave
check_remote_qt_services() {
    local ip=$1
    local video_active=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active gertie-video.service 2>/dev/null" || echo "inactive")
    local capture_active=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active gertie-capture.service 2>/dev/null" || echo "inactive")
    local video_enabled=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-enabled gertie-video.service 2>/dev/null" || echo "disabled")
    local capture_enabled=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-enabled gertie-capture.service 2>/dev/null" || echo "disabled")
    
    # Check if running Qt code (not Tkinter)
    local code_path=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "ps aux | grep video_stream.py | grep -v grep | head -1" 2>/dev/null || echo "")
    local is_qt_code="no"
    if echo "$code_path" | grep -q "camera_system_qt_conversion"; then
        is_qt_code="yes"
    fi
    
    echo "$video_active|$capture_active|$video_enabled|$capture_enabled|$is_qt_code"
}

# Check if old Tkinter services are running
check_old_tkinter_services() {
    local ip=$1
    local video_old=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active video_stream.service 2>/dev/null" || echo "inactive")
    local capture_old=$(ssh -o ConnectTimeout=3 "$REMOTE_USER@$ip" "systemctl is-active still_capture.service 2>/dev/null" || echo "inactive")
    
    if [ "$video_old" = "active" ] || [ "$capture_old" = "active" ]; then
        echo "running"
    else
        echo "stopped"
    fi
}

# Install Qt services on remote slave (only if needed)
install_qt_services() {
    local ip=$1
    local slave_name=$2
    
    log "INFO" "$slave_name: Installing Qt service files..."
    ssh "$REMOTE_USER@$ip" "sudo cp $SOURCE_DIR/gertie-video.service /etc/systemd/system/ && sudo cp $SOURCE_DIR/gertie-capture.service /etc/systemd/system/" 2>&1 | tee -a "$LOG_FILE"
    ssh "$REMOTE_USER@$ip" "sudo systemctl daemon-reload" 2>&1 | tee -a "$LOG_FILE"
    ssh "$REMOTE_USER@$ip" "sudo systemctl enable gertie-video.service gertie-capture.service" 2>&1 | tee -a "$LOG_FILE"
    log "INFO" "$slave_name: Qt services installed and enabled"
}

# Stop old Tkinter services
stop_old_services() {
    local ip=$1
    local slave_name=$2
    
    log "INFO" "$slave_name: Stopping old Tkinter services..."
    ssh "$REMOTE_USER@$ip" "sudo systemctl stop video_stream.service still_capture.service 2>/dev/null || true" 2>&1 | tee -a "$LOG_FILE"
    ssh "$REMOTE_USER@$ip" "sudo systemctl disable video_stream.service still_capture.service 2>/dev/null || true" 2>&1 | tee -a "$LOG_FILE"
}

# Restart Qt services
restart_qt_services() {
    local ip=$1
    local slave_name=$2
    
    log "INFO" "$slave_name: Restarting Qt services..."
    ssh "$REMOTE_USER@$ip" "sudo systemctl restart gertie-video.service gertie-capture.service" 2>&1 | tee -a "$LOG_FILE"
    ((SERVICES_RESTARTED+=2))
}

# Smart sync to remote slave
sync_to_remote() {
    local slave_ip=$1
    local slave_name="rep$((${slave_ip##*.} - 200))"
    local needs_sync=false
    local needs_service_install=false
    local needs_restart=false
    
    echo -e "${CYAN}━━━ Checking $slave_name ($slave_ip) ━━━${NC}"
    
    # Test connectivity
    if ! ping -c 1 -W 2 "$slave_ip" &> /dev/null; then
        echo -e "${RED}✗ $slave_name: Not reachable${NC}"
        log "ERROR" "$slave_name: Not reachable"
        ((SLAVES_FAILED++))
        return 1
    fi
    
    # Check code freshness
    local local_checksum=$(get_local_commit)
    local remote_checksum=$(get_remote_checksum "$slave_ip")
    
    if [ "$local_checksum" != "$remote_checksum" ]; then
        echo -e "${YELLOW}  Code outdated: local=$local_checksum remote=$remote_checksum${NC}"
        needs_sync=true
    else
        echo -e "${GREEN}  ✓ Code up to date ($local_checksum)${NC}"
    fi
    
    # Check Qt services status
    local service_status=$(check_remote_qt_services "$slave_ip")
    IFS='|' read -r video_active capture_active video_enabled capture_enabled is_qt_code <<< "$service_status"
    
    if [ "$video_enabled" != "enabled" ] || [ "$capture_enabled" != "enabled" ]; then
        echo -e "${YELLOW}  Qt services not enabled${NC}"
        needs_service_install=true
    fi
    
    if [ "$video_active" != "active" ] || [ "$capture_active" != "active" ]; then
        echo -e "${YELLOW}  Qt services not running (video=$video_active capture=$capture_active)${NC}"
        needs_restart=true
    else
        echo -e "${GREEN}  ✓ Qt services running${NC}"
    fi
    
    if [ "$is_qt_code" != "yes" ]; then
        echo -e "${YELLOW}  Not running Qt code path${NC}"
        needs_restart=true
    else
        echo -e "${GREEN}  ✓ Running Qt code path${NC}"
    fi
    
    # Check for old Tkinter services
    local old_services=$(check_old_tkinter_services "$slave_ip")
    if [ "$old_services" = "running" ]; then
        echo -e "${YELLOW}  Old Tkinter services still running${NC}"
        needs_restart=true
    fi
    
    # Perform actions if needed
    if $needs_sync || $needs_service_install || $needs_restart; then
        log_section "UPDATING $slave_name ($slave_ip)"
        
        if $needs_sync; then
            log "INFO" "$slave_name: Syncing code..."
            rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
                "$SOURCE_DIR/" "$REMOTE_USER@$slave_ip:$SOURCE_DIR/" 2>&1 | tee -a "$LOG_FILE"
            log "INFO" "$slave_name: Code synced"
        fi
        
        if [ "$old_services" = "running" ]; then
            stop_old_services "$slave_ip" "$slave_name"
        fi
        
        if $needs_service_install; then
            install_qt_services "$slave_ip" "$slave_name"
        fi
        
        if $needs_sync || $needs_restart; then
            # Clear settings files before restart
            ssh "$REMOTE_USER@$slave_ip" "rm -f $SOURCE_DIR/*_settings.json" 2>/dev/null || true
            restart_qt_services "$slave_ip" "$slave_name"
        fi
        
        # Verify
        local new_status=$(check_remote_qt_services "$slave_ip")
        IFS='|' read -r v_act c_act v_en c_en qt_code <<< "$new_status"
        if [ "$v_act" = "active" ] && [ "$c_act" = "active" ]; then
            echo -e "${GREEN}  ✓ $slave_name: Services running${NC}"
            log "INFO" "$slave_name: Update completed successfully"
        else
            echo -e "${RED}  ✗ $slave_name: Services failed to start${NC}"
            log "ERROR" "$slave_name: Services failed to start (video=$v_act capture=$c_act)"
        fi
        
        ((SLAVES_SYNCED++))
    else
        echo -e "${GREEN}  ✓ $slave_name: Already up to date${NC}"
        log "INFO" "$slave_name: Already up to date, skipping"
        ((SLAVES_SKIPPED++))
    fi
}

# Smart sync for local slave (rep8)
sync_to_local() {
    local needs_restart=false
    
    echo -e "${CYAN}━━━ Checking rep8 (local) ━━━${NC}"
    
    # Check local service
    local local_status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "inactive")
    local local_enabled=$(systemctl is-enabled local_camera_slave.service 2>/dev/null || echo "disabled")
    
    if [ "$local_status" != "active" ]; then
        echo -e "${YELLOW}  local_camera_slave.service not running${NC}"
        needs_restart=true
    else
        echo -e "${GREEN}  ✓ local_camera_slave.service running${NC}"
    fi
    
    if [ "$local_enabled" != "enabled" ]; then
        echo -e "${YELLOW}  local_camera_slave.service not enabled${NC}"
        sudo systemctl enable local_camera_slave.service 2>/dev/null || true
    fi
    
    if $needs_restart; then
        log_section "UPDATING rep8 (LOCAL)"
        rm -f "$SOURCE_DIR/rep8_settings.json" 2>/dev/null || true
        log "INFO" "rep8: Restarting local_camera_slave.service..."
        sudo systemctl restart local_camera_slave.service 2>&1 | tee -a "$LOG_FILE"
        ((SERVICES_RESTARTED++))
        
        # Verify
        sleep 1
        local new_status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "inactive")
        if [ "$new_status" = "active" ]; then
            echo -e "${GREEN}  ✓ rep8: Service running${NC}"
            log "INFO" "rep8: Update completed successfully"
        else
            echo -e "${RED}  ✗ rep8: Service failed to start${NC}"
            log "ERROR" "rep8: Service failed to start"
        fi
        ((SLAVES_SYNCED++))
    else
        echo -e "${GREEN}  ✓ rep8: Already up to date${NC}"
        log "INFO" "rep8: Already up to date, skipping"
        ((SLAVES_SKIPPED++))
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

log_section "SMART DEPLOYMENT STARTED"
log "INFO" "Checking system status before deployment..."

LOCAL_COMMIT=$(get_local_commit)
log "INFO" "Local code version: $LOCAL_COMMIT"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   GERTIE Qt Smart Deployment           ║${NC}"
echo -e "${BLUE}║   Checking 8 cameras...                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check and sync all remote slaves
for slave_ip in "${REMOTE_SLAVES[@]}"; do
    sync_to_remote "$slave_ip" || true
    echo ""
done

# Check and sync local slave
sync_to_local
echo ""

# ============================================================================
# SUMMARY
# ============================================================================

log_section "DEPLOYMENT SUMMARY"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Deployment Complete                  ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════╣${NC}"
printf "${BLUE}║${NC}   Slaves synced:    ${GREEN}%-18s${NC}${BLUE}║${NC}\n" "$SLAVES_SYNCED"
printf "${BLUE}║${NC}   Slaves skipped:   ${CYAN}%-18s${NC}${BLUE}║${NC}\n" "$SLAVES_SKIPPED"
printf "${BLUE}║${NC}   Slaves failed:    ${RED}%-18s${NC}${BLUE}║${NC}\n" "$SLAVES_FAILED"
printf "${BLUE}║${NC}   Services restarted: ${YELLOW}%-16s${NC}${BLUE}║${NC}\n" "$SERVICES_RESTARTED"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"

log "INFO" "Slaves synced: $SLAVES_SYNCED | Skipped: $SLAVES_SKIPPED | Failed: $SLAVES_FAILED | Services restarted: $SERVICES_RESTARTED"

# Quick status check
echo ""
echo -e "${CYAN}Final service status:${NC}"
for ip in 201 202 203 204 205 206 207; do
    v=$(ssh -o ConnectTimeout=2 andrc1@192.168.0.$ip "systemctl is-active gertie-video.service" 2>/dev/null || echo "?")
    c=$(ssh -o ConnectTimeout=2 andrc1@192.168.0.$ip "systemctl is-active gertie-capture.service" 2>/dev/null || echo "?")
    if [ "$v" = "active" ] && [ "$c" = "active" ]; then
        echo -e "  rep$((ip-200)): ${GREEN}✓ video=$v capture=$c${NC}"
    else
        echo -e "  rep$((ip-200)): ${RED}✗ video=$v capture=$c${NC}"
    fi
done
local_status=$(systemctl is-active local_camera_slave.service 2>/dev/null || echo "?")
if [ "$local_status" = "active" ]; then
    echo -e "  rep8:  ${GREEN}✓ local=$local_status${NC}"
else
    echo -e "  rep8:  ${RED}✗ local=$local_status${NC}"
fi

log "INFO" "Full log: $LOG_FILE"
echo ""
