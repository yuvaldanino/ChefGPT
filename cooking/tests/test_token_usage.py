from django.test import TestCase
from django.contrib.auth import get_user_model
from cooking.models import ChatSession, Message
from cooking.context_manager import get_relevant_context
import logging
import tiktoken

logger = logging.getLogger(__name__)

def count_tokens(text: str) -> int:
    """Count tokens in a text using tiktoken."""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(text))

class TokenUsageTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a chat session
        self.chat_session = ChatSession.objects.create(
            user=self.user,
            title="Token Usage Test"
        )
        
        # Create a sample recipe
        self.recipe = Message.objects.create(
            chat=self.chat_session,
            role='assistant',
            content='''<h2 data-recipe="title">🍳 Test Recipe</h2>
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
        )
        
        # Create some test messages
        self.messages = [
            Message.objects.create(
                chat=self.chat_session,
                role='user',
                content='Can you make it spicier?'
            ),
            Message.objects.create(
                chat=self.chat_session,
                role='assistant',
                content='I added red pepper flakes to make it spicier.'
            ),
            Message.objects.create(
                chat=self.chat_session,
                role='user',
                content='How long should I cook the pasta?'
            ),
            Message.objects.create(
                chat=self.chat_session,
                role='assistant',
                content='Cook the pasta for 8-10 minutes until al dente.'
            )
        ]

    def test_token_usage_breakdown(self):
        """Test and log token usage for different components."""
        
        # Test 1: Initial recipe request
        logger.info("\n=== Testing Initial Recipe Request ===")
        context = get_relevant_context(self.chat_session, "Give me a recipe for pasta")
        self._analyze_context_tokens(context, "Initial Recipe Request")
        
        # Test 2: Recipe modification
        logger.info("\n=== Testing Recipe Modification ===")
        context = get_relevant_context(self.chat_session, "Make it spicier")
        self._analyze_context_tokens(context, "Recipe Modification")
        
        # Test 3: Cooking question
        logger.info("\n=== Testing Cooking Question ===")
        context = get_relevant_context(self.chat_session, "How long should I cook it?")
        self._analyze_context_tokens(context, "Cooking Question")
        
        # Test 4: General question
        logger.info("\n=== Testing General Question ===")
        context = get_relevant_context(self.chat_session, "What's the best way to store leftovers?")
        self._analyze_context_tokens(context, "General Question")

    def _analyze_context_tokens(self, context, test_name):
        """Analyze and log token usage for each component of the context."""
        total_tokens = 0
        
        logger.info(f"\nAnalyzing {test_name}:")
        logger.info("-" * 50)
        
        for i, msg in enumerate(context):
            tokens = count_tokens(msg['content'])
            total_tokens += tokens
            
            # Categorize the message
            if msg['role'] == 'system':
                if 'recipe' in msg['content'].lower():
                    category = "Recipe System Prompt"
                else:
                    category = "General System Prompt"
            elif 'data-recipe="title"' in msg['content']:
                category = "Recipe Content"
            else:
                category = f"Message {i+1}"
            
            logger.info(f"{category}:")
            logger.info(f"  Tokens: {tokens}")
            logger.info(f"  Role: {msg['role']}")
            logger.info(f"  Content length: {len(msg['content'])} chars")
            logger.info("-" * 30)
        
        logger.info(f"Total tokens for {test_name}: {total_tokens}")
        logger.info("=" * 50) 