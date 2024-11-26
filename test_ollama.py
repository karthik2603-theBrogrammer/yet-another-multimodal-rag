import ollama

response = ollama.chat(
    model='llama3.2-vision:11b',
    messages=[{
        'role': 'user',
        'content': 'What is in this image?',
        'images': ['figures/figure-1-1.jpg'],
        
    }],
    stream = True
)

while response:
    print(next(response))