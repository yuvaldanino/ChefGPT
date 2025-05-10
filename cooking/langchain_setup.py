from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema import HumanMessage, SystemMessage
from .context_manager import classify_message_type, get_relevant_context
import os
from dotenv import load_dotenv

load_dotenv()

def get_recipe_response(chat_session, user_message):
    """Get a response from the LangChain model while maintaining context and formatting."""
    chat = ChatOpenAI(
        temperature=0.7,  # Higher temperature for creativity
        model="gpt-3.5-turbo"
    )

    message_type = classify_message_type(user_message)
    context_messages = get_relevant_context(chat_session, user_message)

    # Base system message
    system_message = """You are ChefGPT, an expert cooking assistant. Your responses must follow these rules:

    1. For recipe creation or modification:
       - Always format recipes in HTML with these exact sections:
         <h2 data-recipe="title">🍳 [Recipe Name]</h2>
         <h3 data-recipe="difficulty">⚡ Difficulty</h3>
         [Easy/Medium/Hard]
         <h3 data-recipe="cuisine">🌍 Cuisine Type</h3>
         [Type of cuisine]
         <h3 data-recipe="prep-time">⏲️ Preparation Time</h3>
         [Time in minutes]
         <h3 data-recipe="servings">👥 Servings</h3>
         [Number of servings]
         <h3 data-recipe="ingredients">📝 Ingredients</h3>
         <ul>
         [List of ingredients with measurements]
         </ul>
         <h3 data-recipe="instructions">📋 Instructions</h3>
         <ol>
         [Numbered steps]
         </ol>
         <h3 data-recipe="tips">💡 Tips</h3>
         <ul>
         [Helpful tips]
         </ul>

    2. For cooking questions:
       - Provide specific, detailed answers
       - Include practical tips
       - Explain the reasoning
       - Keep responses focused and helpful

    3. General rules:
       - Never use generic responses
       - Never ask how you can help
       - Always maintain context from previous messages
       - Always use specific measurements and instructions
       - Always follow modification requests exactly"""

    # Build messages
    messages = [SystemMessage(content=system_message)]
    
    # Add context messages
    for msg in context_messages:
        if msg["role"] == "system":
            messages.append(SystemMessage(content=msg["content"]))
        elif msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(SystemMessage(content=msg["content"]))

    # Add the current message
    messages.append(HumanMessage(content=user_message))

    # Create prompt
    prompt = ChatPromptTemplate.from_messages(messages)

    # Get response
    response = (prompt | chat).invoke({})
    return response.content 