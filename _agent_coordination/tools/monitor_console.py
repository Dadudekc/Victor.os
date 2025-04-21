import os
import time


def count_json_files(folder):
    """Return number of .json files in the given folder."""
    if not os.path.exists(folder):
        return 0
    return len([f for f in os.listdir(folder) if f.endswith('.json')])


def monitor_loop():
    """Continuously clear screen and display task/result counts."""
    tasks_dir = os.path.join('runtime', 'local_blob', 'tasks')
    results_dir = os.path.join('runtime', 'local_blob', 'results')

    while True:
        tasks = count_json_files(tasks_dir)
        results = count_json_files(results_dir)

        os.system('cls' if os.name == 'nt' else 'clear')
        print('📊 Dream.OS Live Monitor')
        print('=========================')
        print(f'🧾 Tasks pending:   {tasks}')
        print(f'✅ Results pending: {results}')
        print('⏳ Refresh every 2s')
        time.sleep(2)


if __name__ == '__main__':
    monitor_loop() 