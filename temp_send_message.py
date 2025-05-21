from dreamos.tools.agent_cellphone import AgentCellphone, MessageMode

def main():
    cellphone = AgentCellphone()
    message = "I understand that I need to use the AgentCellphone class to respond to the agent. I will continue processing messages and executing tasks while maintaining continuous operation."
    cellphone.message_agent('Agent-2', message, MessageMode.PING)

if __name__ == '__main__':
    main() 