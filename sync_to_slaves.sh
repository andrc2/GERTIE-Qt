#!/bin/bash
# Deployment and Logging Script for GERTIE Camera System
# Syncs code to all slaves and logs all system activity to /home/andrc1/Desktop/updatelog.txt

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
LOCAL_SLAVE="127.0.0.1"  # rep8 (local)
SOURCE_DIR="/home/andrc1/camera_system_integrated_final"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    echo "[$TIMESTAMP] [$level] $message" | tee -a "$LOG_FILE"
}

log_section() {
    local section="$1"
    echo "" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    echo "[$TIMESTAMP] $section" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
}

# Start deployment
log_section "DEPLOYMENT STARTED"
log "INFO" "Sync script initiated from control1"
log "INFO" "Source directory: $SOURCE_DIR"
log "INFO" "Target slaves: ${REMOTE_SLAVES[@]} + local (rep8)"

# Git information if available
if [ -d "$SOURCE_DIR/.git" ]; then
    BRANCH=$(cd "$SOURCE_DIR" && git branch --show-current 2>/dev/null || echo "unknown")
    COMMIT=$(cd "$SOURCE_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    log "INFO" "Git branch: $BRANCH | Commit: $COMMIT"
else
    log "WARN" "Not a git repository"
fi

# Function to sync to remote slave
sync_to_remote() {
    local slave_ip=$1
    local slave_name="rep$((${slave_ip##*.} - 200))"
    
    log_section "SYNCING TO $slave_name ($slave_ip)"
    
    # Test connectivity
    if ! ping -c 1 -W 2 "$slave_ip" &> /dev/null; then
        log "ERROR" "$slave_name: Not reachable"
        return 1
    fi
    log "INFO" "$slave_name: Connectivity OK"
    
    # Sync files
    log "INFO" "$slave_name: Starting rsync..."
    if rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
        "$SOURCE_DIR/" "$REMOTE_USER@$slave_ip:$SOURCE_DIR/" 2>&1 | tee -a "$LOG_FILE"; then
        log "INFO" "$slave_name: Rsync completed successfully"
    else
        log "ERROR" "$slave_name: Rsync failed"
        return 1
    fi
    
    # Restart services
    log "INFO" "$slave_name: Clearing old settings files to force fresh initialization..."
    
    # Remove old settings files that might have wrong values
    if ssh "$REMOTE_USER@$slave_ip" "rm -f $SOURCE_DIR/*_settings.json" 2>&1 | tee -a "$LOG_FILE"; then
        log "INFO" "$slave_name: Old settings files cleared"
    else
        log "WARN" "$slave_name: No settings files to clear or failed to clear them"
    fi
    
    log "INFO" "$slave_name: Restarting services..."
    
    # Restart video_stream
    if ssh "$REMOTE_USER@$slave_ip" "sudo systemctl restart video_stream.service" 2>&1 | tee -a "$LOG_FILE"; then
        log "INFO" "$slave_name: video_stream.service restarted"
    else
        log "ERROR" "$slave_name: Failed to restart video_stream.service"
    fi
    
    # Restart still_capture
    if ssh "$REMOTE_USER@$slave_ip" "sudo systemctl restart still_capture.service" 2>&1 | tee -a "$LOG_FILE"; then
        log "INFO" "$slave_name: still_capture.service restarted"
    else
        log "ERROR" "$slave_name: Failed to restart still_capture.service"
    fi
    
    # Check service status
    log "INFO" "$slave_name: Checking service status..."
    ssh "$REMOTE_USER@$slave_ip" "systemctl status video_stream.service still_capture.service --no-pager" 2>&1 | tee -a "$LOG_FILE"
    
    # Check for errors in recent logs
    log "INFO" "$slave_name: Recent service logs (last 20 lines):"
    ssh "$REMOTE_USER@$slave_ip" "journalctl -u video_stream.service -u still_capture.service -n 20 --no-pager" 2>&1 | tee -a "$LOG_FILE"
    
    log "INFO" "$slave_name: Deployment completed"
}

# Function to sync to local slave (rep8)
sync_to_local() {
    log_section "SYNCING TO rep8 (LOCAL)"
    
    log "INFO" "rep8: Clearing old settings files to force fresh initialization..."
    
    # Remove old settings files for local camera
    if rm -f $SOURCE_DIR/rep8_settings.json 2>&1 | tee -a "$LOG_FILE"; then
        log "INFO" "rep8: Old settings file cleared"
    else
        log "WARN" "rep8: No settings file to clear or failed to clear it"
    fi
    
    log "INFO" "rep8: Restarting local services..."
    
    # Restart local services
    if sudo systemctl restart local_camera_slave.service 2>&1 | tee -a "$LOG_FILE"; then
        log "INFO" "rep8: local_camera_slave.service restarted"
    else
        log "ERROR" "rep8: Failed to restart local_camera_slave.service"
    fi
    
    # Check service status
    log "INFO" "rep8: Checking service status..."
    systemctl status local_camera_slave.service --no-pager 2>&1 | tee -a "$LOG_FILE"
    
    # Check for errors in recent logs
    log "INFO" "rep8: Recent service logs (last 20 lines):"
    journalctl -u local_camera_slave.service -n 20 --no-pager 2>&1 | tee -a "$LOG_FILE"
    
    log "INFO" "rep8: Deployment completed"
}

# Deploy to all remote slaves
for slave_ip in "${REMOTE_SLAVES[@]}"; do
    sync_to_remote "$slave_ip" || log "ERROR" "Failed to sync to $slave_ip"
done

# Deploy to local slave (rep8)
sync_to_local

# Summary
log_section "DEPLOYMENT SUMMARY"
log "INFO" "Deployment to all slaves completed"
log "INFO" "Checking network connectivity..."

# Network check
for slave_ip in "${REMOTE_SLAVES[@]}"; do
    if ping -c 1 -W 2 "$slave_ip" &> /dev/null; then
        log "INFO" "$slave_ip: Reachable"
    else
        log "WARN" "$slave_ip: Not reachable"
    fi
done

# System status
log_section "SYSTEM STATUS CHECK"
log "INFO" "Control1 (master) status:"
log "INFO" "Disk usage:"
df -h / 2>&1 | tee -a "$LOG_FILE"

log "INFO" "Memory usage:"
free -h 2>&1 | tee -a "$LOG_FILE"

log "INFO" "CPU temperature:"
vcgencmd measure_temp 2>&1 | tee -a "$LOG_FILE" || log "WARN" "Temperature check not available"

log "INFO" "Network interfaces:"
ip addr show 2>&1 | tee -a "$LOG_FILE"

# Log file location
log_section "DEPLOYMENT COMPLETE"
log "INFO" "Full log saved to: $LOG_FILE"
log "INFO" "Log size: $(du -h "$LOG_FILE" | cut -f1)"
log "INFO" "To view full log: cat $LOG_FILE"
log "INFO" "To view recent errors: grep ERROR $LOG_FILE | tail -20"
log "INFO" "Timestamp: $TIMESTAMP"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully${NC}"
echo -e "${GREEN}Log file: $LOG_FILE${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
