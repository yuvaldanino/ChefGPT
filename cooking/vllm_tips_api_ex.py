# Required packages:
# pip install fastapi uvicorn vllm requests

# To run the server:
# python recipe_api.py

# Test the API:
# Health check: curl http://localhost:8000/health
# Generate tip: curl -X POST http://localhost:8000/generate_tip -H "Content-Type: application/json" -d '{"prompt": "How do I keep onions from making me cry?"}'

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from vllm import LLM, SamplingParams
import uvicorn
from typing import List, Optional

# Initialize FastAPI app
app = FastAPI(title="Cooking Tips API")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your Django app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model and sampling parameters
model = None
sampling_params = None

# Define request and response models
class TipRequest(BaseModel):
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 256  # Reduced for shorter tips
    top_p: Optional[float] = 0.95

class TipResponse(BaseModel):
    tip: str
    tokens_generated: int

@app.on_event("startup")
async def startup_event():
    """Initialize the model when the server starts"""
    global model, sampling_params
    try:
        print("Loading cooking tips model...")
        model = LLM(
            model="ydanino/tinyllama-recipe-merged",
            tensor_parallel_size=1,
            gpu_memory_utilization=0.9,
            trust_remote_code=True
        )
        
        # Default sampling parameters for generating tips
        sampling_params = SamplingParams(
            temperature=0.7,
            top_p=0.95,
            max_tokens=256  # Shorter responses for tips
        )
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        raise

@app.post("/generate_tip", response_model=TipResponse)
async def generate_tip(request: TipRequest):
    """Generate a cooking tip based on the user's prompt"""
    if not model:
        raise HTTPException(status_code=503, detail="Model is not loaded yet")
    
    try:
        # Format the prompt to focus on cooking tips
        formatted_prompt = f"Give me a helpful cooking tip about: {request.prompt}. Keep it concise and practical."
        
        # Update sampling parameters if provided
        current_params = SamplingParams(
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens
        )
        
        # Generate the tip
        outputs = model.generate([formatted_prompt], current_params)
        
        # Get the generated text
        generated_text = outputs[0].outputs[0].text
        
        return TipResponse(
            tip=generated_text,
            tokens_generated=len(outputs[0].outputs[0].token_ids)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Check if the API is healthy and the model is loaded"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "service": "cooking-tips-api"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 