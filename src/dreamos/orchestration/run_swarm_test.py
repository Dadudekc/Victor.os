import os
import sys
import json
import logging
from datetime import datetime
from swarm_cycle_test import SwarmCycleTest

# Configure logging
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'logs', 'swarm_test_runner.log')
REPORT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'test_results', 'swarm_test_report.json')
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, mode='w'),
        logging.StreamHandler()
    ]
)

def generate_report(results):
    """Generates a detailed test report."""
    report = {
        'test_id': results['test_id'],
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_cycles': results['system_metrics']['total_cycles'],
            'successful_cycles': results['system_metrics']['successful_cycles'],
            'failed_cycles': results['system_metrics']['failed_cycles'],
            'average_cycle_time': results['system_metrics']['average_cycle_time'],
            'total_messages_processed': sum(c['messages_processed'] for c in results['cycles']),
            'total_tasks_completed': sum(c['tasks_completed'] for c in results['cycles'])
        },
        'agent_performance': {},
        'errors': [],
        'warnings': [],
        'recommendations': []
    }
    
    # Collect agent performance metrics
    for agent_id, state in results['agent_states'].items():
        report['agent_performance'][agent_id] = {
            'status': state['status'],
            'active_tasks': state['active_tasks'],
            'messages_processed': state['messages'],
            'performance': state['performance']
        }
    
    # Collect errors and warnings
    for cycle in results['cycles']:
        report['errors'].extend(cycle['errors'])
        report['warnings'].extend(cycle['warnings'])
    
    # Generate recommendations
    if report['summary']['failed_cycles'] > 0:
        report['recommendations'].append({
            'type': 'error_handling',
            'priority': 'high',
            'message': 'Implement additional error recovery mechanisms'
        })
    
    if report['summary']['average_cycle_time'] > 1.0:
        report['recommendations'].append({
            'type': 'performance',
            'priority': 'medium',
            'message': 'Investigate cycle time optimization opportunities'
        })
    
    return report

def main():
    logging.info("Starting swarm test runner")
    
    try:
        # Initialize and run the test
        test = SwarmCycleTest()
        results = test.run_test()
        
        # Generate and save report
        report = generate_report(results)
        with open(REPORT_PATH, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\nSwarm Test Summary:")
        print(f"Test ID: {report['test_id']}")
        print(f"Total Cycles: {report['summary']['total_cycles']}")
        print(f"Successful Cycles: {report['summary']['successful_cycles']}")
        print(f"Failed Cycles: {report['summary']['failed_cycles']}")
        print(f"Average Cycle Time: {report['summary']['average_cycle_time']:.2f} seconds")
        print(f"Total Messages Processed: {report['summary']['total_messages_processed']}")
        print(f"Total Tasks Completed: {report['summary']['total_tasks_completed']}")
        
        if report['errors']:
            print("\nErrors encountered:")
            for error in report['errors']:
                print(f"  - {error['agent_id']}: {error['error']}")
        
        if report['warnings']:
            print("\nWarnings:")
            for warning in report['warnings']:
                print(f"  - {warning['agent_id']}: {warning['warning']}")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  - [{rec['priority']}] {rec['message']}")
        
        # Exit with appropriate code
        if report['summary']['failed_cycles'] == 0:
            logging.info("Swarm test completed successfully")
            sys.exit(0)
        else:
            logging.error("Swarm test completed with errors")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"Error running swarm test: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 