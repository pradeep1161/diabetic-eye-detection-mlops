import google.generativeai as genai

class GeminiAPI:
    def __init__(self, api_key):
        if not api_key:
            print("Warning: Gemini API key not provided. Using default recommendations.")
            self.model = None
            return
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        except Exception as e:
            print(f"Error configuring Gemini API: {e}"); self.model = None
    
    def get_recommendations(self, patient_data, analysis_results):
        if not self.model: return self._get_default_recommendations()
        prompt = f"""
        As a medical AI assistant, provide detailed recommendations for a patient with the following information.
        Format the response clearly for a medical report.

        PATIENT DETAILS:
        - Name: {patient_data.get('name', 'N/A')}
        - Age: {patient_data.get('age', 'N/A')}
        - Gender: {patient_data.get('gender', 'N/A')}
        - Diabetes Type: {patient_data.get('diabetesType', 'N/A')}
        - Diabetes Duration: {patient_data.get('diabetesDuration', 'N/A')} years
        - Reported Symptoms: {', '.join(patient_data.get('symptoms', [])) or 'None'}

        EYE ANALYSIS RESULTS:
        """
        if 'fundus' in analysis_results:
            fundus = analysis_results['fundus']
            prompt += f"- Fundus: {fundus['disease'].replace('_', ' ').title()} ({fundus['severity']})\n"
        if 'oct' in analysis_results:
            oct_res = analysis_results['oct']
            prompt += f"- OCT: {oct_res['disease'].replace('_', ' ').title()} ({oct_res['severity']})\n"
        prompt += """
        RECOMMENDATIONS:
        Provide a structured set of recommendations covering:
        1. IMMEDIATE ACTIONS: What to do in the next 1-2 weeks.
        2. LIFESTYLE MODIFICATIONS: Advice on diet, exercise, habits.
        3. MEDICAL FOLLOW-UP: Schedule for seeing specialists.
        4. PREVENTIVE MEASURES: How to prevent progression.
        5. KEY WARNING SIGNS: Symptoms requiring immediate attention.
        """
        try:
            return self.model.generate_content(prompt).text
        except Exception as e:
            print(f"Error getting Gemini recommendations: {e}"); return self._get_default_recommendations()
    
    def get_disease_explanation(self, disease_name):
        """Generates a simple explanation of a disease for a patient."""
        if not self.model:
            return "Detailed explanation is currently unavailable."
        prompt = f"""
        Explain the medical condition '{disease_name.replace('_', ' ')}' in simple, easy-to-understand terms for a patient.
        Structure the explanation with these sections: **What is it?**, **What causes it?**, and **Common Symptoms**.
        Keep the tone reassuring and informative. Do not provide medical advice.
        """
        try:
            return self.model.generate_content(prompt).text
        except Exception as e:
            print(f"Error generating disease explanation: {e}")
            return "Could not generate an explanation at this time."

    def _get_default_recommendations(self):
        return """
        1. IMMEDIATE ACTIONS:
        - Schedule an appointment with an ophthalmologist for a comprehensive eye exam.
        - Discuss these results with your primary care physician or endocrinologist.
        
        2. LIFESTYLE MODIFICATIONS:
        - Strictly monitor and control blood sugar levels.
        - Maintain a healthy diet and engage in regular physical activity.
        
        3. MEDICAL FOLLOW-UP:
        - Follow the appointment schedule recommended by your ophthalmologist.
        
        Disclaimer: This is a default recommendation. Please consult a qualified healthcare provider.
        """
