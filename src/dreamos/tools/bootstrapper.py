import time
from typing import Optional
from .agent_resume.agent_resume import AgentResume

class Bootstrapper:
    def __init__(self, agent_id: str, headless: bool = False):
        self.agent_id = agent_id
        self.headless = headless
        self.agent_resume = AgentResume(agent_id=agent_id, headless=headless)
        
    def start(self) -> None:
        """Start the agent loop"""
        try:
            while True:
                result = self.agent_resume.run_cycle()
                if result is None:
                    print(f"Error in agent cycle for {self.agent_id}")
                    time.sleep(5)  # Wait before retry
                    continue
                    
                # Check for stop conditions
                if result.get("status") == "STOPPED":
                    break
                    
                # Standard cycle delay
                time.sleep(5)
                
        except KeyboardInterrupt:
            print(f"\nGracefully stopping agent {self.agent_id}")
        except Exception as e:
            print(f"Fatal error in agent {self.agent_id}: {e}")
        finally:
            # Cleanup
            self.agent_resume._save_state() 