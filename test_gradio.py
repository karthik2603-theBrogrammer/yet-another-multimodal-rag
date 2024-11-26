from gradio_client import Client, handle_file

client = Client("Aashi/Text-Image-Analyzer")
result = client.predict(
		text="Hello, please explain this image in detail",
		image="figures/figure-1-1.jpg",
		api_name="/predict"
)
print(result)