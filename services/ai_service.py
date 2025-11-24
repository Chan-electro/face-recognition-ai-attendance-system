import os
import pickle
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class AIService:
    """Lightweight AI assistant for answering student queries"""
    
    def __init__(self, model_name='all-MiniLM-L6-v2', embeddings_path=None):
        """Initialize AI service with specified model"""
        self.model_name = model_name
        self.model = None
        self.embeddings_path = embeddings_path
        self.qa_data = []
        self.question_embeddings = None
        self.is_trained = False
    
    def load_model(self):
        """Load the sentence transformer model"""
        if self.model is None:
            print(f"Loading AI model: {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
            print("✓ AI model loaded successfully")
        return self.model
    
    def load_training_data(self, data_folder):
        """Load training data from CSV and text files"""
        self.qa_data = []
        
        # Load FAQs from CSV
        faq_file = os.path.join(data_folder, 'faqs.csv')
        if os.path.exists(faq_file):
            df = pd.read_csv(faq_file)
            for _, row in df.iterrows():
                self.qa_data.append({
                    'question': row['question'],
                    'answer': row['answer'],
                    'category': row.get('category', 'general')
                })
            print(f"✓ Loaded {len(df)} FAQs from faqs.csv")
        
        # Load subject information
        subjects_file = os.path.join(data_folder, 'subjects.csv')
        if os.path.exists(subjects_file):
            df = pd.read_csv(subjects_file)
            for _, row in df.iterrows():
                question = f"What is {row['name']}? Tell me about {row['code']}"
                answer = f"{row['name']} ({row['code']}) is a {row.get('credits', 'N/A')} credit " \
                        f"course taught by {row.get('faculty', 'N/A')}. {row.get('description', '')}"
                self.qa_data.append({
                    'question': question,
                    'answer': answer,
                    'category': 'subjects'
                })
            print(f"✓ Loaded {len(df)} subjects")
        
        # Load policies from text file
        policies_file = os.path.join(data_folder, 'policies.txt')
        if os.path.exists(policies_file):
            with open(policies_file, 'r') as f:
                content = f.read()
                # Split by double newlines for Q&A pairs
                sections = content.strip().split('\n\n')
                for section in sections:
                    if ':' in section:
                        lines = section.split('\n')
                        question = lines[0].replace('Q:', '').strip()
                        answer = '\n'.join(lines[1:]).replace('A:', '').strip()
                        self.qa_data.append({
                            'question': question,
                            'answer': answer,
                            'category': 'policies'
                        })
            print(f"✓ Loaded policies from text file")
        
        print(f"Total QA pairs loaded: {len(self.qa_data)}")
        return len(self.qa_data)
    
    def train(self, data_folder):
        """Train the AI model by generating embeddings"""
        print("\n" + "="*50)
        print("Training AI Model...")
        print("="*50)
        
        # Load model
        self.load_model()
        
        # Load training data
        if self.load_training_data(data_folder) == 0:
            print("⚠ No training data found!")
            return False
        
        # Generate embeddings for all questions
        questions = [qa['question'] for qa in self.qa_data]
        print(f"Generating embeddings for {len(questions)} questions...")
        self.question_embeddings = self.model.encode(questions, show_progress_bar=True)
        
        # Save embeddings if path is provided
        if self.embeddings_path:
            os.makedirs(os.path.dirname(self.embeddings_path), exist_ok=True)
            with open(self.embeddings_path, 'wb') as f:
                pickle.dump({
                    'qa_data': self.qa_data,
                    'embeddings': self.question_embeddings
                }, f)
            print(f"✓ Embeddings saved to {self.embeddings_path}")
        
        self.is_trained = True
        print("="*50)
        print("✓ AI Model training complete!")
        print("="*50 + "\n")
        return True
    
    def load_embeddings(self):
        """Load pre-computed embeddings"""
        if self.embeddings_path and os.path.exists(self.embeddings_path):
            with open(self.embeddings_path, 'rb') as f:
                data = pickle.load(f)
                self.qa_data = data['qa_data']
                self.question_embeddings = data['embeddings']
            
            # Load model for inference
            self.load_model()
            self.is_trained = True
            print(f"✓ Loaded {len(self.qa_data)} pre-trained QA pairs")
            return True
        return False
    
    def ask(self, question, top_k=1, confidence_threshold=0.5):
        """Ask a question and get the best matching answer"""
        if not self.is_trained:
            # Try to load pre-computed embeddings
            if not self.load_embeddings():
                return {
                    'answer': 'AI model is not trained yet. Please contact the administrator.',
                    'confidence': 0.0,
                    'category': 'error'
                }
        
        # Encode the question
        question_embedding = self.model.encode([question])[0]
        
        # Calculate cosine similarity with all stored questions
        similarities = cosine_similarity(
            question_embedding.reshape(1, -1),
            self.question_embeddings
        )[0]
        
        # Get top matches
        top_indices = np.argsort(similarities)[::-1][:top_k]
        top_similarity = similarities[top_indices[0]]
        
        # Check confidence threshold
        if top_similarity < confidence_threshold:
            return {
                'answer': "I'm not sure about that. Could you rephrase your question or ask something else?",
                'confidence': float(top_similarity),
                'category': 'unknown'
            }
        
        # Return best match
        best_match = self.qa_data[top_indices[0]]
        return {
            'answer': best_match['answer'],
            'confidence': float(top_similarity),
            'category': best_match['category'],
            'question': best_match['question']
        }
    
    def get_stats(self):
        """Get AI model statistics"""
        return {
            'is_trained': self.is_trained,
            'total_qa_pairs': len(self.qa_data),
            'model_name': self.model_name,
            'categories': list(set([qa['category'] for qa in self.qa_data]))
        }


# Global AI service instance
_ai_service = None


def get_ai_service(config=None):
    """Get or create AI service singleton"""
    global _ai_service
    
    if _ai_service is None and config:
        _ai_service = AIService(
            model_name=config['AI_MODEL_NAME'],
            embeddings_path=config['AI_EMBEDDINGS_FILE']
        )
        
        # Try to load pre-trained embeddings
        if not _ai_service.load_embeddings():
            # Train if no embeddings exist
            _ai_service.train(config['AI_TRAINING_FOLDER'])
    
    return _ai_service
