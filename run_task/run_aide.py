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
            "OPENAI_API_KEY": "ollama" if selected_network == "ollama" else os.environ.get("OPENAI_API_KEY"),
            "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
            "OPENAI_BASE_URL": base_url,
            "MPLCONFIGDIR": "/tmp",
        },
        tty=True,
        stdin_open=True,
        detach=True,
        mem_limit="32g",
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
        result = container.wait()
        status = result.get("StatusCode", None)
        # Добавьте логирование
        logs = container.logs().decode('utf-8')
        print(f"Контейнер завершился со статусом {status}. Логи:\n{logs}")
        if status != 0:
            print(f"{instructions_file} failed with status {status}")
    finally:
        timer.cancel()
        container.remove(force=True)

 

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs-dir", type=str, default=BASE_PATH / "./logs")
    parser.add_argument("--workspace-dir", type=str, default=BASE_PATH / "./workspaces")
    parser.add_argument("--data-dir", type=str, default=BASE_PATH / "./data")
    parser.add_argument("--submission-dir", type=str, default=BASE_PATH / "./submission")
    parser.add_argument("--instructions-dir", type=str, default=BASE_PATH / "./instructions")
    parser.add_argument("--time-secs", type=int, default=(60 * 60 * 3))
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--code-model", type=str, default="gpt-oss:120b")
    parser.add_argument("--feedback-model", type=str, default="gpt-oss:120b")
    parser.add_argument("--report-model", type=str, default="gpt-oss:120b")
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
        "agent.steps=500 "
        "agent.code.model='{code_model}' "
        "agent.feedback.model='{feedback_model}' "
        "report.model='{report_model}' "
        "agent.search.max_debug_depth=20 "
        "agent.search.debug_prob=1 "
        "agent.expose_prediction=True "
        "exec.timeout=3600 "
        " exp_name={exp_name}"
    )

    TIME_LIMIT_SECS = args.time_secs

    MAX_PARALLEL = args.num_workers

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = []
        for instr_file, exp_name in instruction_map.items():
            command = COMMAND_TEMPLATE.format(
                exp_name=exp_name,
                code_model=args.code_model,
                feedback_model=args.feedback_model,
                time_limit = TIME_LIMIT_SECS,
                report_model=args.report_model
                )
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
                    timeout_sec=TIME_LIMIT_SECS,
                )
            )

        for f in futures:
            f.result()
