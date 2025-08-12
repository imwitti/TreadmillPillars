import os
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient

# OrangePi info
HOST = "192.168.1.118"
USERNAME = "orangepi"
REMOTE_DIR = "/home/orangepi/Documents/TreadmillPillars/TCX"

# Local download folder
LOCAL_DOWNLOAD_DIR = os.path.expanduser("~/Downloads")

def get_latest_tcx_filename(ssh_client):
    # Command to get the most recently modified TCX file in REMOTE_DIR
    # It lists files sorted by modification time (newest first), filtered by .tcx extension
    cmd = f"ls -t {REMOTE_DIR}/*.tcx 2>/dev/null | head -n 1"
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    latest_file = stdout.read().decode().strip()
    return latest_file if latest_file else None

def main():
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    
    print("Connecting to OrangePi...")
    ssh.connect(HOST, username=USERNAME, password="orangepi")  # Add password= or key_filename= if needed
    
    latest_file = get_latest_tcx_filename(ssh)
    if not latest_file:
        print("No TCX files found in the remote directory.")
        ssh.close()
        return
    
    print(f"Latest TCX file found: {latest_file}")
    
    with SCPClient(ssh.get_transport()) as scp:
        local_path = os.path.join(LOCAL_DOWNLOAD_DIR, os.path.basename(latest_file))
        print(f"Downloading to {local_path} ...")
        scp.get(latest_file, local_path)
        print("Download completed.")
    
    ssh.close()

if __name__ == "__main__":
    main()
