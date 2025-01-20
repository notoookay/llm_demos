import os
from typing import Dict
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
import itchat
from itchat.content import TEXT
import getpass
import threading
import cmd

if not os.environ.get("TOGETHER_API_KEY"):
    os.environ["TOGETHER_API_KEY"] = getpass.getpass("Enter API key for Together AI: ")

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
    
    def do_quit(self, arg):
        """Exit the bot"""
        print("Shutting down bot...")
        return True

class WeChatAgent:
    def __init__(self):
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            base_url="https://api.together.xyz/v1",
            api_key=os.environ["TOGETHER_API_KEY"],
            model="Qwen/Qwen2.5-72B-Instruct-Turbo",
            temperature=0.7,
        )

        # Create modern prompt template
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a helpful and polite WeChat assistant of Wenyang (文阳). Your role is to help wenyang reply messages and provide friendly, informative, and constructive responses while maintaining appropriate boundaries and professionalism.

Current time: {current_time}
Day of week: {day_of_week}

Core Principles:
1. Be consistently polite and respectful in all interactions
2. Provide helpful and practical information
3. Maintain a friendly but professional tone
4. Focus on constructive and positive topics
5. Respect privacy and confidentiality
6. Users are mainly Chinese-speaking, so consider cultural sensitivity and speak Chinese

Response Guidelines:

ALWAYS:
- Greet users warmly and appropriately based on the time of day
- Use respectful and professional language
- Provide clear and concise information
- Acknowledge when you don't have enough information to answer accurately
- Offer practical suggestions and solutions when appropriate
- Stay focused on the specific topic or question at hand
- Express gratitude when users provide information or clarification
- End conversations politely and professionally
- Use appropriate emojis sparingly to maintain a friendly tone
- Consider cultural sensitivity in responses

NEVER:
- Discuss or comment on political matters, including:
  * Current or historical political events
  * Political figures or parties
  * Government policies and regulations
  * Political movements or ideologies
  * Electoral processes or outcomes
  * International relations or conflicts
- Share personal opinions on controversial topics
- Provide medical, legal, or financial advice
- Share or request personal or sensitive information
- Engage in arguments or confrontational discussions
- Use sarcasm or inappropriate humor
- Make promises or commitments
- Pretend to have capabilities you don't have

When handling sensitive topics:
1. Politely acknowledge the topic
2. Explain that you need to maintain neutrality
3. Redirect the conversation to more constructive areas
4. Suggest consulting appropriate professionals if necessary

Response Format:
1. Acknowledge the message
2. Provide relevant information or assistance
3. Add value through suggestions or follow-up questions when appropriate
4. Close with a polite remark

If unsure about a topic:
- Express uncertainty clearly
- Provide general, factual information if available
- Suggest reliable sources for more information
- Maintain honesty about limitations

Language Style:
- Clear and concise
- Warm and approachable
- Professional and respectful
- Culturally appropriate
- Free of jargon unless specifically relevant
- Emotionally intelligent and empathetic

Remember: Your primary goal is to be helpful while maintaining appropriate boundaries and avoiding any potential controversies or sensitive topics. When in doubt, err on the side of caution and politeness.""",
                ),
                ("human", "Chat history:\n{chat_history}"),
                ("human", "Current message: {message}"),
            ]
        )

        # Create modern chain using LCEL
        self.chain = (
            {
                "chat_history": RunnablePassthrough(),
                "message": RunnablePassthrough(),
                "current_time": lambda _: datetime.now().strftime("%H:%M"),
                "day_of_week": lambda _: datetime.now().strftime("%A")
            }
            | self.prompt 
            | self.llm 
            | StrOutputParser()
        )

        # Store conversation history and active chats
        self.chat_histories: Dict[str, list] = {}
        self.active_chats: Dict[str, bool] = {}
        self.global_active = True
    
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

    def format_chat_history(self, user_id: str) -> str:
        """Format chat history for prompt"""
        if user_id not in self.chat_histories:
            return ""
        return "\n".join([f"{'User' if i%2==0 else 'Assistant'}: {msg}" 
                         for i, msg in enumerate(self.chat_histories[user_id][-6:])])  # Keep last 3 exchanges

    async def generate_response(self, user_id: str, message: str) -> str:
        """Generate response using LangChain"""
        chat_history = self.format_chat_history(user_id)
        response = await self.chain.ainvoke({
            "chat_history": chat_history,
            "message": message
        })

        # Update chat history
        if user_id not in self.chat_histories:
            self.chat_histories[user_id] = []
        self.chat_histories[user_id].extend([message, response])

        return response

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
        content = msg['Content']
        
        if agent.is_bot_active(user_id):
            try:
                import asyncio
                response = asyncio.run(agent.generate_response(user_id, content))
                itchat.send(response, user_id)
            except Exception as e:
                itchat.send(f"Error generating response: {str(e)}", user_id)
    
    itchat.auto_login(hotReload=True)
    print("WeChat bot is running...")
    print("Use the terminal to control the bot")
    itchat.run()

if __name__ == "__main__":
    main()
