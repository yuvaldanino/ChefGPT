from django.test import TestCase, Client
from django.contrib.auth.models import User
from cooking.models import ChatSession, Message
from cooking.context_manager import get_relevant_context
import time
import json
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

class PerformanceTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Create a chat session
        self.chat_session = ChatSession.objects.create(user=self.user)

    def create_conversation_history(self, message_count):
        """Helper to create a conversation with specified number of messages"""
        recipe_content = """<h2 data-recipe="title">🍳 Authentic Italian Pasta Carbonara</h2>
        <h3 data-recipe="difficulty">⚡ Medium</h3>
        <h3 data-recipe="cuisine">🌍 Italian</h3>
        <h3 data-recipe="prep-time">⏲️ 30 minutes</h3>
        <h3 data-recipe="servings">👥 4 servings</h3>
        <h3 data-recipe="ingredients">📝 Ingredients</h3>
        <ul>
        <li>400g high-quality spaghetti or rigatoni</li>
        <li>200g guanciale or pancetta, diced</li>
        <li>4 large fresh eggs (room temperature)</li>
        <li>100g freshly grated Pecorino Romano</li>
        <li>100g freshly grated Parmigiano-Reggiano</li>
        <li>2-3 cloves garlic, lightly crushed (optional)</li>
        <li>Freshly ground black pepper</li>
        <li>Salt for pasta water</li>
        </ul>
        <h3 data-recipe="instructions">📋 Instructions</h3>
        <ol>
        <li>Bring a large pot of water to boil. Add salt generously.</li>
        <li>In a large bowl, whisk together eggs, grated cheeses, and plenty of black pepper. Set aside.</li>
        <li>In a large pan, cook guanciale over medium heat until crispy and fat has rendered, about 7 minutes.</li>
        <li>Cook pasta in boiling water according to package instructions until al dente.</li>
        <li>Reserve 1 cup of pasta cooking water before draining.</li>
        <li>Working quickly, add hot pasta to pan with guanciale, tossing to coat.</li>
        <li>Remove from heat, add egg mixture, tossing quickly to create a creamy sauce.</li>
        <li>Add pasta water as needed to achieve desired consistency.</li>
        <li>Serve immediately with extra cheese and black pepper.</li>
        </ol>
        <h3 data-recipe="tips">💡 Tips</h3>
        <ul>
        <li>Use room temperature eggs to prevent sauce from seizing</li>
        <li>Never add raw cream - it's not traditional</li>
        <li>Work quickly when combining to prevent eggs from scrambling</li>
        <li>Use freshly grated cheese, not pre-grated</li>
        </ul>"""

        # First message is always the recipe
        Message.objects.create(
            chat=self.chat_session,
            role='assistant',
            content=recipe_content,
            message_type='recipe_creation'
        )

        # Create remaining messages with realistic cooking questions and answers
        qa_pairs = [
            ("How do I know when the pasta is perfectly al dente?", 
             "Test the pasta 1-2 minutes before the package time. It should have a slight bite in the center - firm but not hard. The pasta will continue cooking slightly when mixed with the sauce."),
            ("Can I use bacon instead of guanciale?",
             "While traditional carbonara uses guanciale, you can substitute with pancetta or bacon. The flavor will be slightly different but still delicious. If using bacon, choose a thick-cut variety and avoid smoked bacon if possible."),
            ("My sauce turned out scrambled, what went wrong?",
             "The eggs likely got too hot. To prevent this: 1) Make sure to take the pan off heat before adding the egg mixture, 2) Use room temperature eggs, 3) Toss very quickly to coat the pasta, 4) Add a bit more pasta water if needed to create a creamy sauce."),
            ("Is it okay to add garlic?",
             "While not traditional, adding lightly crushed garlic cloves to the guanciale while it renders adds a subtle flavor. Remove the garlic before adding the pasta if you use it. Many modern Roman restaurants do this, though purists might disagree."),
        ]

        # Add enough Q&A pairs to reach the desired message count
        for i in range((message_count - 1) // 2):
            idx = i % len(qa_pairs)
            question, answer = qa_pairs[idx]
            Message.objects.create(
                chat=self.chat_session,
                role='user',
                content=question,
                message_type='cooking_question'
            )
            Message.objects.create(
                chat=self.chat_session,
                role='assistant',
                content=answer,
                message_type='cooking_question'
            )

        # If we need an odd number of messages, add one more user message
        if message_count % 2 == 0:
            Message.objects.create(
                chat=self.chat_session,
                role='user',
                content="Thank you, this was very helpful!",
                message_type='general_question'
            )

    def measure_context_retrieval_time(self, message_count):
        """Measure time to get context with different approaches"""
        self.create_conversation_history(message_count)

        # Measure old approach (getting all messages)
        start_time = time.time()
        old_context = [{"role": "system", "content": "System prompt"}]
        for msg in Message.objects.filter(chat=self.chat_session).order_by('created_at'):
            old_context.append({
                "role": msg.role,
                "content": msg.content
            })
        old_time = time.time() - start_time
        old_token_estimate = sum(len(msg["content"].split()) * 1.3 for msg in old_context)

        # Measure new approach (using context manager)
        start_time = time.time()
        new_context = get_relevant_context(self.chat_session, "test message")
        new_time = time.time() - start_time
        new_token_estimate = sum(len(msg["content"].split()) * 1.3 for msg in new_context)

        return {
            'old_time': old_time,
            'new_time': new_time,
            'old_context_size': len(old_context),
            'new_context_size': len(new_context),
            'old_token_estimate': old_token_estimate,
            'new_token_estimate': new_token_estimate,
            'token_reduction': ((old_token_estimate - new_token_estimate) / old_token_estimate) * 100 if old_token_estimate > 0 else 0
        }

    def test_performance_comparison(self):
        """Compare performance between old and new approaches"""
        # Test with more realistic conversation lengths
        test_sizes = [15, 25, 50]  # More realistic conversation sizes
        
        for size in test_sizes:
            # Clear any existing messages
            Message.objects.all().delete()
            
            results = self.measure_context_retrieval_time(size)
            
            logger.info(f"\nPerformance test with {size} messages:")
            logger.info(f"Old approach: {results['old_context_size']} messages, ~{int(results['old_token_estimate'])} tokens")
            logger.info(f"New approach: {results['new_context_size']} messages, ~{int(results['new_token_estimate'])} tokens")
            logger.info(f"Token reduction: {results['token_reduction']:.1f}%")
            
            # Verify improvements
            self.assertLess(results['new_context_size'], results['old_context_size'])
            self.assertLess(results['new_token_estimate'], results['old_token_estimate'])
            # For longer conversations, we should see significant token reduction
            if size > 20:
                self.assertGreater(results['token_reduction'], 50)  # Expect at least 50% reduction

    def test_real_world_scenario(self):
        """Test performance in a realistic conversation scenario"""
        # Create a more extensive conversation
        messages = [
            ("user", "Give me a recipe for pasta carbonara", "recipe_creation"),
            ("assistant", """<h2 data-recipe="title">🍳 Pasta Carbonara</h2>
            <h3 data-recipe="difficulty">⚡ Medium</h3>
            <h3 data-recipe="cuisine">🌍 Italian</h3>
            <h3 data-recipe="prep-time">⏲️ 20 minutes</h3>
            <h3 data-recipe="servings">👥 4 servings</h3>
            <h3 data-recipe="ingredients">📝 Ingredients</h3>
            <ul>
            <li>400g spaghetti</li>
            <li>200g pancetta</li>
            <li>4 large eggs</li>
            <li>100g Pecorino Romano</li>
            <li>100g Parmigiano-Reggiano</li>
            <li>Black pepper</li>
            </ul>
            <h3 data-recipe="instructions">📋 Instructions</h3>
            <ol>
            <li>Boil pasta in salted water</li>
            <li>Crisp pancetta in pan</li>
            <li>Mix eggs and cheese</li>
            <li>Combine all ingredients</li>
            </ol>""", "recipe_creation"),
            ("user", "Can you make it spicier?", "recipe_modification"),
            ("assistant", "Here's a spicier version with red pepper flakes...", "recipe_modification"),
            ("user", "How do I know when the pasta is done?", "cooking_question"),
            ("assistant", "The pasta should be al dente...", "cooking_question"),
            ("user", "What temperature should the pan be?", "cooking_question"),
            ("assistant", "Medium-high heat, around 375°F...", "cooking_question"),
            ("user", "Can I use bacon instead of pancetta?", "recipe_modification"),
            ("assistant", "Yes, you can substitute bacon...", "recipe_modification"),
        ]

        for role, content, msg_type in messages:
            Message.objects.create(
                chat=self.chat_session,
                role=role,
                content=content,
                message_type=msg_type
            )

        # Measure context retrieval time
        start_time = time.time()
        context = get_relevant_context(self.chat_session, "Is it ready?")
        context_time = time.time() - start_time

        # Log the context composition
        logger.info("\nContext analysis:")
        logger.info(f"Total context messages: {len(context)}")
        logger.info(f"Context retrieval time: {context_time:.3f}s")
        
        # Verify we maintain recipe context while reducing message count
        recipe_in_context = any('Pasta Carbonara' in msg['content'] for msg in context)
        self.assertTrue(recipe_in_context, "Recipe should be maintained in context")
        self.assertLess(len(context), len(messages) + 1)  # +1 for system prompt 