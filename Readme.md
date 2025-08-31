## Зависимости

1) Классическое питоновское окружение
```bash 
python3 -m venv env 
source env/bin/activate 
pip install -r requirements.txt 
``` 

2) Грузим aide (форк mle-bench)
```bash
git clone https://github.com/WecoAI/aideml.git
```
для запуска нужно определить что используем

a) Если используему не self-hosted модели вроде gpt
```bash
export OPENAI_API_KEY=...
export GEMINI_API_KEY=...
```
б) Для ollama
```bash
export OPENAI_BASE_URL="http://ollama:11434/v1"
```
(Инструкции ниже лучше сделать сразу)

!!!Если выпадает ошибка связанная с max_output_tokens лезем в код aide
```python
# aidem/aide/backend/backend_openai.py:62-63
# коментируем строки
if "max_tokens" in filtered_kwargs:
     filtered_kwargs["max_output_tokens"] = filtered_kwargs.pop("max_tokens")
```

б*) Для gpt-oss в ollama нужно залезть в код aide
```python
# aidem/aide/backend/backend_openai.py:74
# use_chat_api = os.getenv("OPENAI_BASE_URL") is not None and not is_openai_model
#Заменить на
use_chat_api = os.getenv("OPENAI_BASE_URL") is not None
```
## Сборка
### AIDE
Идем в aideml и дописываем

1) 
```bash
# добавляем в requrements.txt
xgboost
catboost
```
2) 
```bash
#Dockerfile блок строк 30-33 заменям
RUN apt-get update && apt-get install -y \
    vim \
    unzip \
    zip \
    p7zip-full \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python-is-python3 \
    build-essential \
    openssh-server \
    gettext \
    ffmpeg \
    libsm6 \
    libxext6 \
    && pip install jupyter \
    && rm -rf /var/lib/apt/lists/*
```
3)
```python
# aide/interpreter.py:138 добавляем после global_scope (огромная дыра при exec без scope, нужно пул реквест отправить)
          global_scope: dict = {}
        import types
        main_mod = types.ModuleType("__main__")
        main_mod.__file__ = self.agent_file_name
        sys.modules["__main__"] = main_mod
        global_scope = main_mod.__dict__
```

4) Сборка образа
```bash
docker build --platform=linux/amd64 -t aide aideml
```

### ollama:
```bash
docker compose -f ollama/docker-compose.yaml  up -d
...
```
Загрузка модели
```bash
docker exec -it ollama ollama pull <model>
```

## Подготовка данных
1) Качаем данные, сплитим с сидом
```python
from sklearn.model_selection import train_test_split
import numpy as np
import random

random.seed(42)
np.random.seed(42)

train, test = train_test_split(dfc, shuffle=True, random_state=42)
```
и засовываем полученый train.csv в run_task/data

2) Для файлов с описаниями, вроде (Arab.csv) генерируем промпт бенча
(встречаются аномалии с разными полями в dataframe)
```bash
#examples
#id - номер задачи
#csv - путь к csv файлу
#task-suf - суффикс языка в инструкции
#instruction-path - путь куда положить собраный промпт
#csv-sep по дефолту ",", некоторые данные имеют разделитель ";"

python prepare/task_builder.py --id=10 --csv=competitions/Chineese_25.csv --task-suf="cn" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=10 --csv=competitions/Arab_25.csv --task-suf="arab" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=10 --csv=competitions/English_25.csv --task-suf="en" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=10 --csv=competitions/Italian_25.csv --task-suf="it" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=10 --csv=competitions/Japanese_25.csv --task-suf="jp" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=10 --csv=competitions/Kazach_25.csv --task-suf="kz" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=10 --csv=competitions/Polish_25.csv --task-suf="pl" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=10 --csv=competitions/Romanian_25.csv --task-suf="ro" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=10 --csv=competitions/Spanish_25.csv --task-suf="es" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=10 --csv=competitions/Turkish_25.csv --task-suf="tr" --instruction-path=run_task/instructions
```

## Запуск
Устанавливаем максимальное время на воркера и число воркеров
```bash
#доп параметр
python run_task/run_aide.py --time-secs=10800 --num-workers=3 --code-model="gpt-oss:120b" --feedback-model="gpt-oss:120b" --report-model="gpt-oss:120b"
```

## Валидация
Грейдера здесь нет (увы), поэтому аккуратно храним код который получился, потом прогоним что получилось и посчитаем метрики