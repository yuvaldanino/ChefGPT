from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
from .db_connection import get_db_connection

load_dotenv()

# Initialize OpenAI embeddings with minimal configuration
embeddings = OpenAIEmbeddings()  # Let it use default configuration

def generate_recipe_embedding(recipe):
    """
    Generate embedding for a recipe using LangChain.
    
    Args:
        recipe (dict): Recipe data including title, ingredients, instructions, etc.
    
    Returns:
        dict: Recipe data with embedding
    """
    # Combine recipe components into a single text
    recipe_text = f"""
    Title: {recipe['title']}
    Cuisine: {recipe['cuisine']}
    Difficulty: {recipe['difficulty']}
    Ingredients: {', '.join(recipe['ingredients'])}
    Instructions: {' '.join(recipe['instructions'])}
    Tips: {', '.join(recipe['tips'])}
    """
    
    # Generate embedding
    embedding = embeddings.embed_query(recipe_text)
    
    # Add embedding to recipe data
    recipe['embedding'] = embedding
    
    return recipe

def store_recipe_embedding(recipe):
    """
    Store recipe with its embedding in Supabase using direct SQL.
    
    Args:
        recipe (dict): Recipe data with embedding
    
    Returns:
        dict: Stored recipe data
    """
    try:
        # Prepare data for Supabase
        recipe_data = {
            'title': recipe['title'],
            'cuisine': recipe['cuisine'],
            'difficulty': recipe['difficulty'],
            'ingredients': recipe['ingredients'],
            'instructions': recipe['instructions'],
            'tips': recipe['tips'],
            'embedding': recipe['embedding']
        }
        
        print("Attempting to store recipe with data:", recipe_data)
        
        # Connect to database and insert data
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.recipe_embeddings 
                    (title, cuisine, difficulty, ingredients, instructions, tips, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, title, cuisine, difficulty, ingredients, instructions, tips, created_at, updated_at
                """, (
                    recipe_data['title'],
                    recipe_data['cuisine'],
                    recipe_data['difficulty'],
                    recipe_data['ingredients'],
                    recipe_data['instructions'],
                    recipe_data['tips'],
                    recipe_data['embedding']
                ))
                
                result = cur.fetchone()
                conn.commit()
                
                if result:
                    return {
                        'id': result[0],
                        'title': result[1],
                        'cuisine': result[2],
                        'difficulty': result[3],
                        'ingredients': result[4],
                        'instructions': result[5],
                        'tips': result[6],
                        'created_at': result[7],
                        'updated_at': result[8]
                    }
                else:
                    raise Exception("No data returned after insert")
            
    except Exception as e:
        print(f"Error details: {str(e)}")
        raise

def find_similar_recipes(recipe, limit=5):
    """
    Find similar recipes using vector similarity search.
    
    Args:
        recipe (dict): Recipe to compare against
        limit (int): Number of similar recipes to return
    
    Returns:
        list: Similar recipes
    """
    # Generate embedding for the input recipe
    recipe_with_embedding = generate_recipe_embedding(recipe)
    
    # Query Supabase for similar recipes
    result = supabase.rpc(
        'match_recipes',
        {
            'query_embedding': recipe_with_embedding['embedding'],
            'match_threshold': 0.7,
            'match_count': limit
        }
    ).execute()
    
    return result.data if result.data else []

def update_recipe_embedding(recipe_id, recipe):
    """
    Update recipe embedding in Supabase.
    
    Args:
        recipe_id (int): ID of the recipe to update
        recipe (dict): Updated recipe data
    
    Returns:
        dict: Updated recipe data
    """
    # Generate new embedding
    recipe_with_embedding = generate_recipe_embedding(recipe)
    
    # Update in Supabase
    result = supabase.table('recipe_embeddings').update({
        'title': recipe['title'],
        'cuisine': recipe['cuisine'],
        'difficulty': recipe['difficulty'],
        'ingredients': recipe['ingredients'],
        'instructions': recipe['instructions'],
        'tips': recipe['tips'],
        'embedding': recipe_with_embedding['embedding']
    }).eq('id', recipe_id).execute()
    
    return result.data[0] if result.data else None

def delete_recipe_embedding(recipe_id):
    """
    Delete recipe embedding from Supabase.
    
    Args:
        recipe_id (int): ID of the recipe to delete
    
    Returns:
        bool: True if successful
    """
    result = supabase.table('recipe_embeddings').delete().eq('id', recipe_id).execute()
    return bool(result.data)

def get_recipe_recommendations(user_embedding, user_id, limit=5):
    """
    Find recipe recommendations for a user based on their embedding.
    
    Args:
        user_embedding (list): The user's embedding vector
        user_id (int): The user's ID to exclude their saved recipes
        limit (int): Number of recommendations to return
    
    Returns:
        list: Recommended recipes with their similarity scores
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # First get the IDs of recipes the user has already saved
                cur.execute("""
                    SELECT embedding_id 
                    FROM cooking_savedrecipe 
                    WHERE user_id = %s AND embedding_id IS NOT NULL
                """, (user_id,))
                saved_recipe_ids = [row[0] for row in cur.fetchall()]
                
                # If user has no saved recipes, return empty list
                if not saved_recipe_ids:
                    return []
                
                # Find similar recipes using cosine similarity
                # Exclude recipes the user has already saved
                cur.execute("""
                    WITH user_embedding AS (
                        SELECT %s::vector AS embedding
                    )
                    SELECT 
                        re.id,
                        re.title,
                        re.cuisine,
                        re.difficulty,
                        re.ingredients,
                        re.instructions,
                        re.tips,
                        1 - (re.embedding <=> (SELECT embedding FROM user_embedding)) as similarity
                    FROM public.recipe_embeddings re
                    WHERE re.id != ALL(%s)
                    ORDER BY similarity DESC
                    LIMIT %s
                """, (user_embedding, saved_recipe_ids, limit))
                
                results = cur.fetchall()
                
                # Format the results
                recommendations = []
                for row in results:
                    recommendations.append({
                        'id': row[0],
                        'title': row[1],
                        'cuisine': row[2],
                        'difficulty': row[3],
                        'ingredients': row[4],
                        'instructions': row[5],
                        'tips': row[6],
                        'similarity_score': float(row[7])
                    })
                
                return recommendations
                
    except Exception as e:
        print(f"Error getting recommendations: {str(e)}")
        raise 