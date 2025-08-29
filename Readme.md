## Зависимости

1) Классическое питоновское окружение
```bash 
python3 -m venv env 
source env/bin/activate 
pip install -r requirements.txt 
``` 

2) Грузим aide
```bash
git clone https://github.com/WecoAI/aideml.git
```
для запуска нужно определить что используем

a) Если используему не self-hosted модели вроде gpt
```bash
exprot OPENAI_API_KEY=...
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
Образ ранера
```bash
docker build -t aide aideml
```

Запуск ollama:
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

python prepare/task_builder.py --id=14 --csv=competitions/Chineese_25.csv --task-suf="cn" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=14 --csv=competitions/Arab_25.csv --task-suf="arab" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=14 --csv=competitions/English_25.csv --task-suf="en" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=14 --csv=competitions/Italian_25.csv --task-suf="it" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=14 --csv=competitions/Japanese_25.csv --task-suf="jp" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=14 --csv=competitions/Kazach_25.csv --task-suf="kz" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=14 --csv=competitions/Polish_25.csv --task-suf="pl" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=14 --csv=competitions/Romanian_25.csv --task-suf="ro" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=14 --csv=competitions/Spanish_25.csv --task-suf="es" --instruction-path=run_task/instructions

python prepare/task_builder.py --id=14 --csv=competitions/Turkish_25.csv --task-suf="tr" --instruction-path=run_task/instructions
```

## Запуск
Устанавливаем максимальное время на воркера и число воркеров
```bash
python run_task/run_aide.py --time-secs=10800 --num-workers=3
```

## Валидация
Грейдера здесь нет (увы), поэтому аккуратно храним код который получился, потом прогоним что получилось и посчитаем метрики