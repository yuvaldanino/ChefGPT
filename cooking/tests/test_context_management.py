from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from cooking.models import ChatSession, Message
from cooking.context_manager import classify_message_type, create_conversation_summary, get_relevant_context
import json
import logging

logger = logging.getLogger(__name__)

class ContextManagementTest(TestCase):
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
        
        logger.info("Test setup complete")

    def test_message_classification(self):
        """Test that messages are correctly classified"""
        test_cases = [
            ("Give me a recipe for pasta", "recipe_creation"),
            ("Make it spicier", "recipe_modification"),
            ("How long should I cook it?", "cooking_question"),
            ("Thanks!", "general_question"),
        ]
        
        for message, expected_type in test_cases:
            msg_type = classify_message_type(message)
            self.assertEqual(msg_type, expected_type)
            logger.info(f"Message '{message}' correctly classified as {msg_type}")

    def test_conversation_flow(self):
        """Test a complete conversation flow with context management"""
        
        # Step 1: Initial recipe request
        response = self.client.post(
            reverse('send_message', args=[self.chat_session.id]),
            {'message': 'Give me a recipe for pasta carbonara'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        logger.info("Initial recipe request successful")
        
        # Verify message was saved and classified correctly
        initial_message = Message.objects.filter(
            chat=self.chat_session,
            role='user'
        ).first()
        self.assertEqual(initial_message.message_type, 'recipe_creation')
        
        # Step 2: Recipe modification
        response = self.client.post(
            reverse('send_message', args=[self.chat_session.id]),
            {'message': 'Make it spicier please'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        logger.info("Recipe modification request successful")
        
        # Step 3: Cooking question
        response = self.client.post(
            reverse('send_message', args=[self.chat_session.id]),
            {'message': 'How do I know when the pasta is done?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        logger.info("Cooking question successful")
        
        # Add more messages to trigger summarization
        for i in range(8):  # This will bring total messages to >10
            self.client.post(
                reverse('send_message', args=[self.chat_session.id]),
                {'message': f'Test message {i}'}
            )
        
        # Verify summarization occurred
        self.chat_session.refresh_from_db()
        self.assertIsNotNone(self.chat_session.recipe_summary)
        self.assertTrue(self.chat_session.last_summary_at > 0)
        logger.info("Summarization verification successful")
        
        # Test context retrieval
        context = get_relevant_context(self.chat_session, "test message")
        self.assertTrue(any('recipe' in msg['content'].lower() for msg in context))
        self.assertTrue(len(context) >= 2)  # Should have at least system prompt and summary
        logger.info(f"Context retrieval successful, got {len(context)} messages")

    def test_summary_creation(self):
        """Test that summaries are created correctly"""
        # Create a recipe message
        Message.objects.create(
            chat=self.chat_session,
            role='assistant',
            content='<h2 data-recipe="title">🍳 Test Recipe</h2>',
            message_type='recipe_creation'
        )
        
        # Create a modification
        Message.objects.create(
            chat=self.chat_session,
            role='assistant',
            content='Modified to be spicier',
            message_type='recipe_modification'
        )
        
        # Create a Q&A pair
        Message.objects.create(
            chat=self.chat_session,
            role='user',
            content='How long to cook?',
            message_type='cooking_question'
        )
        Message.objects.create(
            chat=self.chat_session,
            role='assistant',
            content='Cook for 10 minutes',
            message_type='cooking_question'
        )
        
        # Create summary
        summary = create_conversation_summary(self.chat_session)
        
        # Verify summary contains all important parts
        self.assertIn('Test Recipe', summary)
        self.assertIn('spicier', summary)
        self.assertIn('How long to cook?', summary)
        logger.info("Summary creation test successful") 