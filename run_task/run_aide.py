#!/usr/bin/env python3
import os
import docker
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import threading

BASE_PATH = Path(__file__).resolve().parent

def run_aide_container_with_timeout(
    image: str,
    command: str,
    logs_dir: str,
    workspace_dir: str,
    data_dir: str,
    submission_dir: str,
    instructions_file: str,
    timeout_sec: int = 60,
):
    client = docker.from_env()

    logs_dir = os.path.abspath(logs_dir)
    workspace_dir = os.path.abspath(workspace_dir)
    data_dir = os.path.abspath(data_dir)
    instructions_file = os.path.abspath(instructions_file)

    volumes = {
        logs_dir: {"bind": "/app/logs", "mode": "rw"},
        workspace_dir: {"bind": "/app/workspaces", "mode": "rw"},
        data_dir: {"bind": "/home/data", "mode": "rw"},
        instructions_file: {"bind": "/home/instructions.txt", "mode": "ro"},
        submission_dir: {"bind": "/home/submission", "mode": "rw"}
    }

    network_name = "ollama"
    base_url = os.environ.get("OPENAI_BASE_URL", None)
    selected_network = None
    if base_url:
        try:
            client.networks.get(network_name)
            selected_network = network_name
        except docker.errors.NotFound:
            raise RuntimeError("For run ollama need ollama network")
    else:
        base_url = "https://api.openai.com/v1"

    print(command)
    container = client.containers.run(
        image=image,
        command=command,
        volumes=volumes,
        environment={
            "OPENAI_API_KEY": "pass",
            "OPENAI_BASE_URL": base_url,
            "MPLCONFIGDIR": "/tmp"
        },
        detach=True,
        auto_remove=True,
        stdin_open=False,
        tty=False,
        network=selected_network
    )


    def kill_container():
        try:
            print(f"{instructions_file} timeout reached, killing container...")
            container.kill()
        except Exception:
            pass

    timer = threading.Timer(timeout_sec, kill_container)
    timer.start()

    try:
        # Посмотреть вывод контейнера в реальном времени
        for line in container.logs(stream=True):
            print(line.decode().strip())

        result = container.wait()
        print(f"{instructions_file} finished with status:", result.get("StatusCode"))
    except docker.errors.APIError:
        print(f"{instructions_file} timeout reached, killing container...")
        container.kill()
    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs-dir", type=str, default=BASE_PATH / "./logs")
    parser.add_argument("--workspace-dir", type=str, default=BASE_PATH / "./workspaces")
    parser.add_argument("--data-dir", type=str, default=BASE_PATH / "./data")
    parser.add_argument("--submission-dir", type=str, default=BASE_PATH / "./submission")
    parser.add_argument("--instructions-dir", type=str, default=BASE_PATH / "./instructions")
    parser.add_argument("--time-secs", type=int, default=(60 * 60 * 3))
    parser.add_argument("--num-workers", type=int, default=1)
    args = parser.parse_args()

    LOGS_DIR = Path(args.logs_dir).resolve()
    WORKSPACE_BASE = Path(args.workspace_dir).resolve()
    DATA_DIR = Path(args.data_dir).resolve()
    INSTRUCTIONS_DIR = Path(args.instructions_dir).resolve()
    SUBMISSION_DIR = Path(args.submission_dir).resolve()
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_BASE.mkdir(parents=True, exist_ok=True)

    instruction_files = sorted(INSTRUCTIONS_DIR.glob("instruction_*.txt"))

    instruction_map = {
        str(f): f.stem.replace("instruction_", "") for f in instruction_files
    }

    COMMAND_TEMPLATE = (
        "data_dir=/home/data/ desc_file=/home/instructions.txt "
        "agent.code.model='gpt-oss:120b' "
        "agent.feedback.model='gpt-oss:120b' "
        "report.model='gpt-oss:120b' " 
        " exp_name={exp_name}"
    )

    TIME_LIMIT_SECS = args.time_secs

    MAX_PARALLEL = args.num_workers

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = []
        for instr_file, exp_name in instruction_map.items():
            command = COMMAND_TEMPLATE.format(exp_name=exp_name)
            futures.append(
                executor.submit(
                    run_aide_container_with_timeout,
                    image="aide",
                    command=command,
                    logs_dir=LOGS_DIR,
                    workspace_dir=WORKSPACE_BASE,
                    data_dir=DATA_DIR,
                    submission_dir=SUBMISSION_DIR,
                    instructions_file=instr_file,
                    timeout_sec=TIME_LIMIT_SECS
                )
            )

        for f in futures:
            f.result()