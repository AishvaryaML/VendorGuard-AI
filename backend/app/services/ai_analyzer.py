import ollama

def analyze_policy(policy_text):

    prompt = f"""
You are a cybersecurity and privacy expert.

Read the following privacy policy and provide:

1. A short summary.
2. Major privacy risks.
3. Security strengths.
4. Final overall risk level (Low, Medium, High).

Privacy Policy:

{policy_text[:5000]}
"""

    response = ollama.chat(
        model="llama3.2:latest",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]