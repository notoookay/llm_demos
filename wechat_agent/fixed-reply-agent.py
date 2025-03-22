import os
from typing import Dict
import itchat
from itchat.content import TEXT
import getpass
import threading
import cmd

class WeChatTerminal(cmd.Cmd):
    prompt = 'WeChat Bot > '
    
    def __init__(self, agent):
        super().__init__()
        self.agent = agent
    
    def do_enable(self, arg):
        """Enable bot globally or for specific user ID: enable [user_id]"""
        if arg:
            self.agent.enable_bot(arg)
            print(f"Bot enabled for user {arg}")
        else:
            self.agent.enable_all()
            print("Bot enabled globally")
    
    def do_disable(self, arg):
        """Disable bot globally or for specific user ID: disable [user_id]"""
        if arg:
            self.agent.disable_bot(arg)
            print(f"Bot disabled for user {arg}")
        else:
            self.agent.disable_all()
            print("Bot disabled globally")
    
    def do_list(self, arg):
        """List all active users"""
        active_users = self.agent.get_active_users()
        print("\nActive users:")
        for user in active_users:
            print(f"- {user}")
    
    def do_message(self, arg):
        """Change the fixed reply message: message [new message]"""
        if arg:
            self.agent.set_fixed_message(arg)
            print(f"Fixed message changed to: '{arg}'")
        else:
            print(f"Current fixed message: '{self.agent.fixed_message}'")
    
    def do_quit(self, arg):
        """Exit the bot"""
        print("Shutting down bot...")
        return True

class WeChatAgent:
    def __init__(self):
        # Fixed reply message
        self.fixed_message = "有事请留言！"
        
        # Store active chats
        self.active_chats: Dict[str, bool] = {}
        self.global_active = True
    
    def set_fixed_message(self, message: str):
        """Set the fixed reply message"""
        self.fixed_message = message
    
    def enable_bot(self, user_id: str):
        """Enable bot for specific user"""
        self.active_chats[user_id] = True
    
    def disable_bot(self, user_id: str):
        """Disable bot for specific user"""
        self.active_chats[user_id] = False
    
    def enable_all(self):
        """Enable bot globally"""
        self.global_active = True
    
    def disable_all(self):
        """Disable bot globally"""
        self.global_active = False
    
    def get_active_users(self) -> list:
        """Get list of active users"""
        return [user_id for user_id, active in self.active_chats.items() if active]
    
    def is_bot_active(self, user_id: str) -> bool:
        """Check if bot is active for a specific user"""
        if not self.global_active:
            return False
        return self.active_chats.get(user_id, True)  # Default to True if user not in list

    def generate_response(self, user_id: str, message: str) -> str:
        """Generate fixed response"""
        return self.fixed_message

def terminal_thread(agent):
    terminal = WeChatTerminal(agent)
    terminal.cmdloop("WeChat Bot Terminal Control\nType 'help' for commands")

def main():
    agent = WeChatAgent()
    
    # Start terminal thread
    thread = threading.Thread(target=terminal_thread, args=(agent,), daemon=True)
    thread.start()
    
    @itchat.msg_register(TEXT)
    def text_reply(msg):
        user_id = msg['FromUserName']
        
        if agent.is_bot_active(user_id):
            try:
                response = agent.generate_response(user_id, "")
                itchat.send(response, user_id)
            except Exception as e:
                print(f"Error sending response: {str(e)}")
    
    # Login to WeChat
    itchat.auto_login(hotReload=True)
    print("WeChat bot is running...")
    print("Use the terminal to control the bot")
    print(f"Current fixed message: '{agent.fixed_message}'")
    itchat.run()

if __name__ == "__main__":
    main()
