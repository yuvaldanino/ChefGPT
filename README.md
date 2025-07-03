
# Chef ChatGPT 🍳🧠

Check it out ! http://chefgpt-alb-1911712359.us-east-1.elb.amazonaws.com/home/

An AI-powered recipe assistant that generates personalized recipes, chat responses, and intelligent food recommendations using LLMs, embeddings, and scalable cloud infrastructure.
![Blank diagram (2)](https://github.com/user-attachments/assets/6a8b1771-2d56-4dd0-bfcd-ca8047fda3e6)

---

## 🚀 Overview

Chef ChatGPT is a production-ready web application that allows users to:
- Chat with an AI chef to generate recipes based on ingredients, preferences, or questions
- Get personalized recipe recommendations using vector embeddings
- Save, view, and interact with recipes in a responsive UI

---

## 🧱 Tech Stack

- **Backend**: Django, Python, Supabase (PostgreSQL + Vectors), Celery, Redis
- **LLM**: OpenAI API, fine-tuned Hugging Face model
- **Inference**: vLLM on GPU EC2 with FastAPI
- **Frontend**: Django templates
- **Infra**: AWS EC2, Docker, NGINX, Gunicorn, ALB
- **DevOps**: GitHub Actions, CloudWatch

---

## 🧠 AI Features

### 🗣️ Context-Aware Chat

- Built with **LangChain** to manage long-term context in conversations
- Reduced OpenAI API token usage by 60% through context summarization and prompt optimization

### 🍲 Fine-Tuned Recipe Model

- Fine-tuned a Hugging Face model for recipe generation using **PyTorch + LoRA**
- Trained on a CUDA-enabled EC2 GPU instance, achieving 5× faster training time
- Served via **vLLM + FastAPI** for low-latency inference (3× faster than standard)

👉 **[View Model Training Repo](https://github.com/yuvaldanino/recipe_data/tree/main)**

---

## 📊 Recommendations Engine

- User embeddings are generated using OpenAI embedding API
- Supabase + pgvector used for **cosine similarity**-based search
- Recommendations run as background Celery tasks for non-blocking performance
- Achieved 70% reduction in recommendation time

---

## ⚙️ Deployment Architecture

- Dockerized app deployed on multiple EC2 instances behind an AWS **Application Load Balancer**
- Scalable request handling via **NGINX + Gunicorn**
- CI/CD pipeline using **GitHub Actions**
- Monitoring and logging via **CloudWatch**

---

## 🧪 Testing & Monitoring

- Unit, integration, and performance tests across backend
- Real-time monitoring and alerting with AWS CloudWatch

---




