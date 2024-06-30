import os
import subprocess

def kill_qdrant_instances_one():
    try:
        # Replace this command with the appropriate one for your OS
        if os.name == 'nt':  # Windows
            subprocess.run(['taskkill', '/F', '/IM', 'qdrant.exe'])
        else:  # Unix-like
            subprocess.run(['pkill', '-f', 'qdrant'])
    except Exception as e:
        print(f"Error terminating Qdrant instances: {e}")

import psutil

def kill_qdrant_instances_two():
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'qdrant' in proc.info['name']:
                os.kill(proc.info['pid'], 9)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass