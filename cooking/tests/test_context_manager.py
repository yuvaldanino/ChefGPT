from django.test import TestCase
from django.contrib.auth import get_user_model
from cooking.models import ChatSession, Message
from cooking.context_manager import get_relevant_context, classify_message_type
import logging

logger = logging.getLogger(__name__)

class ContextManagerTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a chat session
        self.chat_session = ChatSession.objects.create(
            user=self.user,
            title="Test Chat"
        )
        
        # Create some test messages
        self.messages = [
            Message.objects.create(
                chat=self.chat_session,
                role='user',
                content='Can you give me a recipe for pasta?'
            ),
            Message.objects.create(
                chat=self.chat_session,
                role='assistant',
                content='''<h2 data-recipe="title">🍳 Simple Pasta Recipe</h2>
<h3 data-recipe="difficulty">⚡ Easy</h3>
Easy
<h3 data-recipe="cuisine">🌍 Italian</h3>
Italian
<h3 data-recipe="prep-time">⏲️ 20 minutes</h3>
20 minutes
<h3 data-recipe="servings">👥 2 servings</h3>
2 servings
<h3 data-recipe="ingredients">📝 Ingredients</h3>
<ul>
<li>200g pasta</li>
<li>2 tbsp olive oil</li>
<li>2 cloves garlic</li>
</ul>
<h3 data-recipe="instructions">📋 Instructions</h3>
<ol>
<li>Boil pasta</li>
<li>Heat oil and garlic</li>
<li>Combine and serve</li>
</ol>
<h3 data-recipe="tips">💡 Tips</h3>
<ul>
<li>Add salt to pasta water</li>
</ul>'''
            ),
            Message.objects.create(
                chat=self.chat_session,
                role='user',
                content='Can you make it spicier?'
            ),
            Message.objects.create(
                chat=self.chat_session,
                role='assistant',
                content='''<h2 data-recipe="title">🍳 Spicy Pasta Recipe</h2>
<h3 data-recipe="difficulty">⚡ Easy</h3>
Easy
<h3 data-recipe="cuisine">🌍 Italian</h3>
Italian
<h3 data-recipe="prep-time">⏲️ 20 minutes</h3>
20 minutes
<h3 data-recipe="servings">👥 2 servings</h3>
2 servings
<h3 data-recipe="ingredients">📝 Ingredients</h3>
<ul>
<li>200g pasta</li>
<li>2 tbsp olive oil</li>
<li>2 cloves garlic</li>
<li>1 tsp red pepper flakes</li>
</ul>
<h3 data-recipe="instructions">📋 Instructions</h3>
<ol>
<li>Boil pasta</li>
<li>Heat oil, garlic, and red pepper flakes</li>
<li>Combine and serve</li>
</ol>
<h3 data-recipe="tips">💡 Tips</h3>
<ul>
<li>Add salt to pasta water</li>
<li>Adjust spice level to taste</li>
</ul>'''
            )
        ]
        
        # Create some long messages to test token limits
        long_message = "This is a very long message " * 100  # Creates a long message
        self.long_messages = [
            Message.objects.create(
                chat=self.chat_session,
                role='user',
                content=long_message
            ) for _ in range(3)
        ]

    def test_context_manager(self):
        # Test basic context retrieval
        context = get_relevant_context(self.chat_session, "Can you make it less spicy?")
        
        # Check that we have the recipe in context
        self.assertTrue(any('data-recipe="title"' in msg['content'] for msg in context))
        
        # Check that we have recent messages
        self.assertTrue(len(context) > 2)  # Should have system prompt + recipe + some messages
        
        # Test token limits with long messages
        context = get_relevant_context(self.chat_session, "What about adding cheese?")
        
        # Count total tokens in context
        total_tokens = sum(len(msg['content'].split()) for msg in context)
        logger.info(f"Total tokens in context: {total_tokens}")
        
        # Verify we're not exceeding our token limit
        self.assertLess(total_tokens, 3000)  # Should be well under our limit
        
        # Test message type classification
        message_type = classify_message_type("Can you make it less spicy?")
        self.assertEqual(message_type, "recipe_modification")
        
        # Test that we're not including too many messages
        self.assertLessEqual(len([m for m in context if m['role'] != 'system']), 6) 