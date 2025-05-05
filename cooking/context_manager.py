from typing import List, Dict
import re
from .models import ChatSession, Message
import logging

# Configure logging
logger = logging.getLogger(__name__)

def classify_message_type(content: str) -> str:
    """
    Classify the type of message based on its content.
    """
    content_lower = content.lower()
    
    # Check for recipe creation patterns
    if any(phrase in content_lower for phrase in [
        "recipe for", "how to make", "how do i make", "can you give me a recipe",
        "i want to make", "create a recipe", "write a recipe"
    ]):
        logger.info(f"Message classified as recipe_creation: {content[:50]}...")
        return "recipe_creation"
    
    # Check for recipe modification patterns
    if any(phrase in content_lower for phrase in [
        "modify", "change", "adjust", "instead of", "substitute",
        "make it", "can we", "could we", "spicier", "sweeter"
    ]):
        logger.info(f"Message classified as recipe_modification: {content[:50]}...")
        return "recipe_modification"
    
    # Check for cooking question patterns
    if any(phrase in content_lower for phrase in [
        "how do i", "what temperature", "how long", "when should i",
        "is it done", "what does it mean", "how can i tell", "what if"
    ]):
        logger.info(f"Message classified as cooking_question: {content[:50]}...")
        return "cooking_question"
    
    logger.info(f"Message classified as general_question: {content[:50]}...")
    return "general_question"

def create_conversation_summary(chat_session: ChatSession) -> str:
    """
    Create a summary of the conversation, focusing on the recipe and important modifications.
    """
    logger.info(f"Creating summary for chat session {chat_session.id}")
    
    # Get all unsummarized messages
    messages = Message.objects.filter(
        chat=chat_session,
        is_summarized=False
    ).order_by('created_at')
    
    logger.info(f"Found {messages.count()} unsummarized messages")
    
    if not messages.exists():
        logger.info("No messages to summarize, returning existing summary")
        return chat_session.recipe_summary or ""

    # Initialize summary sections
    recipe_content = ""
    modifications = []
    important_qa = []
    
    for msg in messages:
        if msg.role == 'assistant' and '<h2 data-recipe="title">' in msg.content:
            logger.info("Found recipe content in message")
            recipe_content = msg.content
        elif msg.message_type == 'recipe_modification' and msg.role == 'assistant':
            logger.info("Found recipe modification")
            modifications.append(msg.content)
        elif msg.message_type == 'cooking_question':
            logger.info("Found cooking Q&A")
            question = msg.content
            answer = Message.objects.filter(
                chat=chat_session,
                created_at__gt=msg.created_at
            ).first()
            if answer and answer.role == 'assistant':
                important_qa.append(f"Q: {question}\nA: {answer.content}")
    
    # Build the summary
    summary_parts = []
    
    if recipe_content:
        summary_parts.append("CURRENT RECIPE:\n" + recipe_content)
    
    if modifications:
        summary_parts.append("MODIFICATIONS:\n" + "\n".join(modifications[-3:]))  # Keep last 3 modifications
    
    if important_qa:
        summary_parts.append("IMPORTANT Q&A:\n" + "\n".join(important_qa[-3:]))  # Keep last 3 Q&As
    
    # Mark messages as summarized
    messages.update(is_summarized=True)
    
    # Update chat session
    summary = "\n\n".join(summary_parts)
    chat_session.recipe_summary = summary
    chat_session.last_summary_at = chat_session.message_count
    chat_session.save()
    
    logger.info(f"Created summary with {len(summary_parts)} sections")
    return summary

def get_relevant_context(chat_session: ChatSession, current_message: str) -> List[Dict[str, str]]:
    """
    Get the relevant context for the current message.
    """
    logger.info(f"Getting context for chat session {chat_session.id}")
    
    context = []
    
    # First, find the most recent recipe message
    recipe_message = Message.objects.filter(
        chat=chat_session,
        content__contains='<h2 data-recipe="title">',
        role='assistant'
    ).order_by('-created_at').first()

    # If we have a recipe, add it first
    if recipe_message:
        logger.info("Found and adding recipe to context")
        context.append({
            "role": "system",
            "content": f"Current recipe context:\n{recipe_message.content}"
        })

    # Add the system prompt with formatting instructions only if needed
    if "recipe" in current_message.lower() or not recipe_message:
        logger.info("Adding recipe formatting instructions")
        context.append({
            "role": "system",
            "content": """You are ChefGPT, an expert cooking assistant. You help users with recipes, cooking techniques, and culinary advice. Be friendly, professional, and focus on providing accurate cooking information.

When providing recipes, always use this format with exact spacing and line breaks:
<h2 data-recipe="title">🍳 [Recipe Name]</h2>

<h3 data-recipe="difficulty">⚡ Difficulty</h3>
[Easy/Medium/Hard]

<h3 data-recipe="cuisine">🌍 Cuisine Type</h3>
[Type of cuisine e.g. Italian, Mexican, Japanese, etc.]

<h3 data-recipe="prep-time">⏲️ Preparation Time</h3>
[Prep time details]

<h3 data-recipe="servings">👥 Servings</h3>
[Number of servings]

<h3 data-recipe="ingredients">📝 Ingredients</h3>
<ul>
[List ingredients with measurements]
</ul>

<h3 data-recipe="instructions">📋 Instructions</h3>
<ol>
[Numbered steps for cooking]
</ol>

<h3 data-recipe="tips">💡 Tips</h3>
<ul>
[Optional cooking tips and variations]
</ul>"""
        })
    else:
        logger.info("Adding simplified system prompt")
        context.append({
            "role": "system",
            "content": "You are ChefGPT, an expert cooking assistant. Help with cooking techniques and answer questions about the current recipe."
        })

    # Get recent relevant messages
    recent_messages = Message.objects.filter(
        chat=chat_session
    ).order_by('-created_at')[:4]
    
    logger.info(f"Adding {recent_messages.count()} recent messages to context")
    
    # Add them in chronological order
    for msg in reversed(recent_messages):
        context.append({
            "role": msg.role,
            "content": msg.content
        })
    
    logger.info(f"Total context messages: {len(context)}")
    return context 