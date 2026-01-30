from langchain_core.prompts import PromptTemplate

general_prompt = PromptTemplate.from_template("""
    You are a personal assistant and you name is Void. Respond to the input professionally as a personal assistant.
    Give the response in in points, dont summarize
    Query: {review}
    Answer:
""")

# MODEL = "llama3:8b"
# MODEL = "llama3-groq-tool-use:latest"

BIO_LABELS = [
    "O",
    "B-Pickup_pincode","I-Pickup_pincode",
    "B-Delivery_pincode","I-Delivery_pincode",
    "B-cod","I-cod",
    "B-total_order_value","I-total_order_value",
    "B-is_return","I-is_return",
    "B-prepaid","I-prepaid",
    "B-weight_unit","I-weight_unit",
    "B-weight","I-weight",
]

temp_token = ''

