import pandas as pd
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
import argparse
BASE_TEMPLATE_PATH = Path(__file__).parent.resolve() / "bench_templates"

class TaskBuilder:
    def __init__(self, templates_path: str | Path = BASE_TEMPLATE_PATH):
        self.env = Environment(loader=FileSystemLoader(templates_path))
        self.base_template = self.env.get_template('base_instructions.j2')
    
    def render(self, description, domain, metric, datacard):
        context = {
            "code_extention": ".py",
            "language": "python",
            "competition_type_code": True,
            "competition_type_file": False,
            "code_template_variant": "extended",
            "task_info": {
                "description": description,
                "domain": domain,
                "metric": metric,
                "datacard": datacard
            },
        }
        rendered = self.base_template.render(**context)
        return rendered

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=int, required=True)
    parser.add_argument('--csv', type=str, required=True)
    parser.add_argument('--task-suf', type=str, required=True)
    parser.add_argument('--instruction-path', type=str, required=True)
    parser.add_argument('--csv-sep', type=str, default=',')
    args = parser.parse_args()
    data_path = Path(args.csv).resolve()
    task_info = pd.read_csv(data_path, sep=args.csv_sep).iloc[args.id]
    tb = TaskBuilder()
    res = tb.render(task_info.description, task_info.domain, task_info.metric, task_info.data_card)
    instruction_path = Path(args.instruction_path).resolve()
    instruction_path.mkdir(parents=True, exist_ok=True)
    with open(instruction_path / f"instruction_{args.task_suf}.txt", 'w') as f:
        f.write(res)
