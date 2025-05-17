from celery import shared_task
import logging
from .models import UserEmbedding, SavedRecipe
from .db_connection import get_db_connection
import numpy as np
import json

logger = logging.getLogger(__name__)

@shared_task
def test_celery_task():
    """
    A simple test task to verify Celery is working properly.
    """
    logger.info("Test Celery task is running!")
    return "Celery is working!"

@shared_task
def update_user_embedding(user_id):
    """
    Calculate user embedding by averaging their saved recipe embeddings,
    find similar recipes, and store both the embedding and recommendations.
    """
    try:
        # Get all saved recipes for the user
        saved_recipes = SavedRecipe.objects.filter(user_id=user_id)
        
        if not saved_recipes.exists():
            logger.info(f"No saved recipes found for user {user_id}")
            return None
            
        # Get embeddings from Supabase
        embeddings = []
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for recipe in saved_recipes:
                    if recipe.embedding_id:
                        cur.execute("""
                            SELECT embedding 
                            FROM public.recipe_embeddings 
                            WHERE id = %s
                        """, (recipe.embedding_id,))
                        result = cur.fetchone()
                        if result and result[0]:
                            # Convert the embedding to a numpy array
                            try:
                                # If the embedding is already a list, use it directly
                                if isinstance(result[0], list):
                                    embedding = result[0]
                                # If it's a string, try to parse it as JSON
                                elif isinstance(result[0], str):
                                    embedding = json.loads(result[0])
                                else:
                                    embedding = result[0]
                                
                                # Convert to numpy array and ensure it's float
                                embedding_array = np.array(embedding, dtype=np.float32)
                                embeddings.append(embedding_array)
                            except Exception as e:
                                logger.error(f"Error processing embedding for recipe {recipe.id}: {str(e)}")
                                continue
        
        if not embeddings:
            logger.info(f"No valid embeddings found for user {user_id}'s recipes")
            return None
            
        # Calculate average embedding
        avg_embedding = np.mean(embeddings, axis=0).tolist()
        
        # Get saved recipe IDs to exclude
        saved_recipe_ids = [recipe.embedding_id for recipe in saved_recipes if recipe.embedding_id]
        logger.info(f"Excluding user's saved recipe IDs: {saved_recipe_ids}")
        
        # Find similar recipes
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # First, verify we have recipes to recommend
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM public.recipe_embeddings 
                    WHERE id != ALL(%s)
                """, (saved_recipe_ids,))
                available_recipes = cur.fetchone()[0]
                logger.info(f"Found {available_recipes} recipes available for recommendations")
                
                # Get recommendations
                cur.execute("""
                    WITH user_embedding AS (
                        SELECT %s::vector AS embedding
                    )
                    SELECT 
                        re.id,
                        1 - (re.embedding <=> (SELECT embedding FROM user_embedding)) as similarity,
                        re.title  -- Moved title to the end
                    FROM public.recipe_embeddings re
                    WHERE re.id != ALL(%s)
                    ORDER BY similarity DESC
                    LIMIT 5
                """, (avg_embedding, saved_recipe_ids))
                
                recommendations = []
                for row in cur.fetchall():
                    recommendations.append({
                        'recipe_id': row[0],
                        'similarity_score': float(row[1])
                    })
                    logger.info(f"Recommended recipe ID: {row[0]}, Title: {row[2]}, Score: {float(row[1]):.3f}")
        
        # Update or create user embedding with recommendations
        user_embedding, created = UserEmbedding.objects.update_or_create(
            user_id=user_id,
            defaults={
                'embedding': avg_embedding,
                'recommendations': recommendations
            }
        )
        
        logger.info(f"Successfully updated embedding and recommendations for user {user_id}")
        return user_embedding.id
        
    except Exception as e:
        logger.error(f"Error updating user embedding for user {user_id}: {str(e)}")
        raise 