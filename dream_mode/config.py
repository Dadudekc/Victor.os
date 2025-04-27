import os
import argparse


def load_config():
    parser = argparse.ArgumentParser(description="SwarmController Config")
    parser.add_argument("--connection-string", dest="connection_string", help="Azure storage connection string")
    parser.add_argument("--sas-token", dest="sas_token", help="Azure SAS token")
    parser.add_argument("--container-name", dest="container_name", default="dream-os-c2", help="Azure Blob container name")
    parser.add_argument("--fleet-size", dest="fleet_size", type=int, default=int(os.getenv("FLEET_SIZE", "3")), help="Number of Cursor agents in the swarm")
    parser.add_argument("--stats-interval", dest="stats_interval", type=int, default=int(os.getenv("STATS_INTERVAL", "60")), help="Seconds between automatic stats snapshots")
    args = parser.parse_args()
    connection_string = args.connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    sas_token = args.sas_token or os.getenv("AZURE_STORAGE_SAS_TOKEN")
    return {
        "connection_string": connection_string,
        "sas_token": sas_token,
        "container_name": args.container_name,
        "fleet_size": args.fleet_size,
        "stats_interval": args.stats_interval
    } 
