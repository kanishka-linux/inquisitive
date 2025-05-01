import subprocess
import sys
import os
import time
import signal
import atexit
import argparse
import requests
from frontend.config import settings as fe_settings
from backend.config import settings as be_settings

# Store process objects
processes = []


def start_backend(port=8000, log_level="debug"):
    """Start the FastAPI backend server."""
    print(f"Starting backend server on port {port}...")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--reload",
        f"--port={port}",
        f"--log-level={log_level}"
    ]

    # Start the process
    process = subprocess.Popen(
        cmd,
        text=True,
        # Use shell=True on Windows
        shell=sys.platform == "win32",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    processes.append((process))
    return process


def start_frontend(port=8501):
    """Start the Streamlit frontend."""
    print(f"Starting Streamlit frontend on port {port}...")
    custom_env = {
        "STREAMLIT_SERVER_HEADLESS": "true",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"
    }
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/app.py",
        f"--server.port={port}"
    ]

    # Start the process
    process = subprocess.Popen(
        cmd,
        text=True,
        env=custom_env,
        # Use shell=True on Windows
        shell=sys.platform == "win32",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    processes.append((process))
    return process


def start_frontend_separately():
    """Start the Streamlit frontend."""
    print(f"Starting Streamlit frontend on port {fe_settings.SERVER_PORT}...")
    custom_env = {
        "STREAMLIT_SERVER_HEADLESS": "true",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"
    }
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/app.py",
        f"--server.port={fe_settings.SERVER_PORT}",
        f"--server.address={fe_settings.SERVER_HOST}"
    ]

    # Start the process
    process = subprocess.Popen(
        cmd,
        text=True,
        env=custom_env,
        # Use shell=True on Windows
        shell=sys.platform == "win32",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append((process))

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Received interrupt signal. Shutting down...")
        cleanup()
        sys.exit(0)


def cleanup():
    """Clean up processes when the launcher exits."""
    print("Shutting down all services...")
    for process in processes:
        try:
            # Send SIGTERM to process
            if sys.platform == "win32":
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)

            # Close log files
        except Exception as e:
            print(f"Error during cleanup: {e}")


def is_backend_ready():
    try:
        response = requests.get(
            f"{fe_settings.API_URL}/ping",
            timeout=5
        )
        if response.status_code == 200:
            return True
    except requests.exceptions.Timeout:
        print("backend API server trying to be ready, please wait..")
    except requests.exceptions.ConnectionError:
        print("backend takes some time to start on the first run, please wait..")

    return False


def start_all(backend_port=8000, frontend_port=8501, log_level="debug"):
    """Start all services."""
    # Register cleanup handler
    atexit.register(cleanup)

    # Start backend
    start_backend(port=backend_port, log_level=log_level)

    for i in range(0, 600, 5):
        if is_backend_ready():
            break
        else:
            time.sleep(5)

    # Start frontend
    start_frontend(port=frontend_port)

    print(
        f"All services started. Backend on port {backend_port}, Frontend on port {frontend_port}")
    print("Press Ctrl+C to stop all services")

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Received interrupt signal. Shutting down...")
        cleanup()
        sys.exit(0)


def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Start Inquisitive backend and frontend services")
    parser.add_argument(
        "--backend-port",
        type=int,
        default=be_settings.SERVER_PORT,
        help="Port for the backend server"
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=fe_settings.SERVER_PORT,
        help="Port for the frontend server"
    )
    parser.add_argument(
        "--log-level",
        default=be_settings.SERVER_LOG_LEVEL,
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level for the backend server"
    )

    args = parser.parse_args()

    start_all(
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()
