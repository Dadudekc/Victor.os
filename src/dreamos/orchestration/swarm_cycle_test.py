import os
import json
import time
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configure logging
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'logs', 'swarm_cycle_test.log')
TEST_RESULTS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'test_results', 'swarm_cycle_results.json')

os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
os.makedirs(os.path.dirname(TEST_RESULTS_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, mode='w'),
        logging.StreamHandler()
    ]
)

class SwarmCycleTest:
    def __init__(self):
        self.test_results = {
            'test_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'start_time': None,
            'end_time': None,
            'cycles': [],
            'agent_states': {},
            'system_metrics': {
                'total_cycles': 0,
                'successful_cycles': 0,
                'failed_cycles': 0,
                'average_cycle_time': 0
            }
        }
        self.workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        self.agent_mailboxes = os.path.join(self.workspace_root, 'runtime', 'agent_comms', 'agent_mailboxes')

    def inject_episode_kickoff(self):
        """Injects episode kickoff message into all agent inboxes."""
        logging.info("Injecting episode kickoff message into agent inboxes...")
        
        kickoff_message = {
            'type': 'episode_kickoff',
            'timestamp': datetime.now().isoformat(),
            'episode_id': 'LAUNCH-FINAL-LOCK',
            'message': 'Episode kickoff initiated for swarm cycle test'
        }

        for agent_dir in os.listdir(self.agent_mailboxes):
            if agent_dir.startswith('Agent-'):
                inbox_path = os.path.join(self.agent_mailboxes, agent_dir, 'inbox.json')
                if os.path.exists(inbox_path):
                    try:
                        with open(inbox_path, 'r') as f:
                            inbox = json.load(f)
                    except json.JSONDecodeError:
                        inbox = []
                    if isinstance(inbox, dict):
                        inbox = [inbox]
                    elif not isinstance(inbox, list):
                        inbox = []
                    inbox.append(kickoff_message)
                    with open(inbox_path, 'w') as f:
                        json.dump(inbox, f, indent=2)
                    
                    logging.info(f"Injected kickoff message into {agent_dir}'s inbox")

    def observe_cycle(self, cycle_number: int) -> Dict:
        """Observes a single cycle of agent operations."""
        cycle_start = time.time()
        cycle_data = {
            'cycle_number': cycle_number,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'agent_states': {},
            'messages_processed': 0,
            'tasks_completed': 0,
            'errors': [],
            'warnings': [],
            'performance_metrics': {
                'cycle_duration': 0,
                'message_processing_time': 0,
                'task_processing_time': 0
            }
        }

        # Check agent states
        for agent_dir in os.listdir(self.agent_mailboxes):
            if agent_dir.startswith('Agent-'):
                agent_id = agent_dir
                status_path = os.path.join(self.agent_mailboxes, agent_dir, 'status.json')
                tasks_path = os.path.join(self.agent_mailboxes, agent_dir, 'tasks.yaml')
                inbox_path = os.path.join(self.agent_mailboxes, agent_dir, 'inbox.json')
                
                agent_state = {
                    'status': 'unknown',
                    'active_tasks': 0,
                    'messages': 0,
                    'last_update': None,
                    'performance': {
                        'cpu_usage': 0,
                        'memory_usage': 0,
                        'response_time': 0
                    }
                }
                
                # Check status
                try:
                    with open(status_path, 'r') as f:
                        status = json.load(f)
                        agent_state['status'] = status.get('status', 'unknown')
                        agent_state['last_update'] = status.get('last_update')
                        if 'performance' in status:
                            agent_state['performance'].update(status['performance'])
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    cycle_data['warnings'].append({
                        'agent_id': agent_id,
                        'warning': f'Could not read status: {str(e)}'
                    })
                
                # Check tasks
                try:
                    with open(tasks_path, 'r') as f:
                        tasks = yaml.safe_load(f)
                        if isinstance(tasks, list):
                            agent_state['active_tasks'] = len(tasks)
                            cycle_data['tasks_completed'] += sum(1 for t in tasks if t.get('status') == 'completed')
                except (FileNotFoundError, yaml.YAMLError) as e:
                    cycle_data['warnings'].append({
                        'agent_id': agent_id,
                        'warning': f'Could not read tasks: {str(e)}'
                    })
                
                # Check messages
                try:
                    with open(inbox_path, 'r') as f:
                        inbox = json.load(f)
                        if isinstance(inbox, dict) and 'messages' in inbox:
                            agent_state['messages'] = len(inbox['messages'])
                            cycle_data['messages_processed'] += len(inbox['messages'])
                        elif isinstance(inbox, list):
                            agent_state['messages'] = len(inbox)
                            cycle_data['messages_processed'] += len(inbox)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    cycle_data['warnings'].append({
                        'agent_id': agent_id,
                        'warning': f'Could not read inbox: {str(e)}'
                    })
                
                cycle_data['agent_states'][agent_id] = agent_state
                
                if agent_state['status'] == 'error':
                    cycle_data['errors'].append({
                        'agent_id': agent_id,
                        'error': 'Agent reported error state'
                    })

        cycle_data['end_time'] = datetime.now().isoformat()
        cycle_data['performance_metrics']['cycle_duration'] = time.time() - cycle_start
        
        return cycle_data

    def run_test(self, num_cycles: int = 25):
        """Runs the swarm cycle test."""
        logging.info(f"Starting swarm cycle test with {num_cycles} cycles")
        self.test_results['start_time'] = datetime.now().isoformat()
        
        # Inject episode kickoff
        self.inject_episode_kickoff()
        
        # Run cycles
        for cycle in range(1, num_cycles + 1):
            logging.info(f"Starting cycle {cycle}/{num_cycles}")
            cycle_data = self.observe_cycle(cycle)
            self.test_results['cycles'].append(cycle_data)
            
            # Update system metrics
            self.test_results['system_metrics']['total_cycles'] += 1
            if not cycle_data['errors']:
                self.test_results['system_metrics']['successful_cycles'] += 1
            else:
                self.test_results['system_metrics']['failed_cycles'] += 1
            
            # Calculate average cycle time
            cycle_times = [c['performance_metrics']['cycle_duration'] for c in self.test_results['cycles']]
            self.test_results['system_metrics']['average_cycle_time'] = sum(cycle_times) / len(cycle_times)
            
            # Save intermediate results
            self.save_results()
            
            # Wait between cycles
            time.sleep(1)
        
        self.test_results['end_time'] = datetime.now().isoformat()
        self.save_results()
        logging.info("Swarm cycle test completed")
        
        return self.test_results

    def save_results(self):
        """Saves test results to file."""
        try:
            with open(TEST_RESULTS_PATH, 'w') as f:
                json.dump(self.test_results, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving test results: {e}")

def main():
    test = SwarmCycleTest()
    results = test.run_test()
    
    # Print summary
    print("\nSwarm Cycle Test Summary:")
    print(f"Total Cycles: {results['system_metrics']['total_cycles']}")
    print(f"Successful Cycles: {results['system_metrics']['successful_cycles']}")
    print(f"Failed Cycles: {results['system_metrics']['failed_cycles']}")
    print(f"Average Cycle Time: {results['system_metrics']['average_cycle_time']:.2f} seconds")
    
    if results['system_metrics']['failed_cycles'] > 0:
        print("\nErrors encountered:")
        for cycle in results['cycles']:
            if cycle['errors']:
                print(f"\nCycle {cycle['cycle_number']}:")
                for error in cycle['errors']:
                    print(f"  - {error['agent_id']}: {error['error']}")

if __name__ == "__main__":
    main() 