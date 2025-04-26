#!/usr/bin/env python3
import os
import argparse
from social.utils.chatgpt_scraper import ChatGPTScraper


def main():
    parser = argparse.ArgumentParser(prog="brainstorm_tank", description="Forum-style multi-agent brainstorming tool using ChatGPTScraper")
    parser.add_argument("--topic", required=True, help="Topic or directive for brainstorming")
    parser.add_argument("--viewpoints", required=True, nargs='+', help="List of agent viewpoints to simulate")
    args = parser.parse_args()

    print(f"Brainstorming on topic: '{args.topic}' with viewpoints: {args.viewpoints}\n")
    scraper = ChatGPTScraper(headless=True)
    with scraper as sc:
        history = sc.get_conversation_history()
        if not history:
            print("[brainstorm_tank] No existing conversation found.")
            return
        conv_id = history[0].get('id')
        for vp in args.viewpoints:
            print(f"--- Viewpoint: {vp} ---")
            prompt = f"You are an agent with viewpoint: {vp}. Provide your perspective on: {args.topic}"
            try:
                sc.send_message(conv_id, prompt)
                messages = sc.get_conversation_messages(conv_id)
                text = messages[-1].get('content', '') if messages else ''
            except Exception as e:
                text = f"[Error generating response with ChatGPTScraper: {e}]"
            print(text + "\n")

if __name__ == "__main__":
    main() 
