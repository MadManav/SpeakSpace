from matplotlib import pyplot as plt
import io
import base64
from collections import defaultdict
from .models import Feedback

def get_latest_ratings(username, topic, limit=5):
    """Get the latest 5 ratings for a specific user and topic"""
    ratings = Feedback.objects.filter(
        username=username,
        topic=topic
    ).order_by('-id')[:limit]  # Get latest 5 feedbacks
    
    return list(reversed([feedback.rating for feedback in ratings]))

def generate_topic_plot(username, topic):
    plt.figure(figsize=(10, 6))
    
    # Get latest 5 ratings for this user and topic
    ratings = get_latest_ratings(username, topic)
    
    if ratings:
        # Fixed x-axis labels
        tests = ["Test 1", "Test 2", "Test 3", "Test 4", "Test 5"][:len(ratings)]
        
        plt.plot(tests, ratings, marker='o')
        plt.xlabel("Tests")
        plt.ylabel("Rating")
        plt.title(f"{topic} Ratings for {username}")
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Set y-axis limits
        plt.ylim(0, 5)  # Assuming ratings are from 0 to 5
        
        # Save plot to a bytes buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        
        # Convert to base64 for HTML embedding
        image_png = buffer.getvalue()
        graph = base64.b64encode(image_png).decode('utf-8')
        graph_uri = f'data:image/png;base64,{graph}'
        
        plt.close()
        return graph_uri
    
    plt.close()
    return None