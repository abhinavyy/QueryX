import google.generativeai as genai

genai.configure(api_key="AIzaSyAihHsRhes-4-J_LbAhuJUV78r7-tb2SZM")

models = genai.list_models()
for m in models:
    print(m.name, m.supported_generation_methods)
