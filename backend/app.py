import os, traceback, numpy as np, tensorflow as tf, mlflow, base64, cv2
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from config import Config
from utils.pdf_generator import PDFGenerator
from utils.image_processor import ImageProcessor
from utils.gemini_api import GeminiAPI

load_dotenv()
app = Flask(__name__); app.config.from_object(Config); CORS(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True); os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)

def load_model_from_registry(model_name, stage="Production"):
    try:
        model_uri = f"models:/{model_name}/{stage}"; print(f"Loading model '{model_name}' from stage '{stage}'...")
        model = mlflow.keras.load_model(model_uri); print(f"Model '{model_name}' loaded successfully.")
        return model
    except Exception as e:
        print(f"Error loading model '{model_name}' from MLflow Registry: {e}"); return None

mlflow.set_tracking_uri("file:./mlruns")
fundus_model = load_model_from_registry('fundus-model')
oct_model = load_model_from_registry('oct-model')
image_processor = ImageProcessor(); pdf_generator = PDFGenerator(app.config['REPORTS_FOLDER']); gemini_api = GeminiAPI(os.getenv("GEMINI_API_KEY"))

def allowed_file(filename): return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

def predict(model, image_path, image_type, class_list):
    if model is None: return "Model not loaded", 0.0, "Unknown", None, None
    try:
        img_array = image_processor.preprocess_fundus(image_path) if image_type == 'fundus' else image_processor.enhance_oct(image_path)
        img_batch = np.expand_dims(img_array, axis=0)
        preprocessed_batch = tf.keras.applications.efficientnet_v2.preprocess_input(img_batch)
        predictions = model.predict(preprocessed_batch); confidence = float(np.max(predictions[0]))
        predicted_class_idx = np.argmax(predictions[0]); class_name = class_list[predicted_class_idx]
        severity = get_severity(class_name, confidence, image_type)
        heatmap_b64, original_b64 = None, None
        if class_name != 'normal':
            last_conv_layer = [layer for layer in model.layers if isinstance(layer, tf.keras.layers.Conv2D)][-1].name
            heatmap_b64 = image_processor.generate_grad_cam(model, img_array, last_conv_layer)
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))
        original_b64 = base64.b64encode(buffer).decode('utf-8')
        return class_name, confidence, severity, heatmap_b64, original_b64
    except Exception as e:
        traceback.print_exc(); return "Prediction Error", 0.0, str(e), None, None

def get_severity(disease, confidence, image_type):
    severity_mappings = Config.SEVERITY_LEVELS[image_type].get(disease)
    if not severity_mappings: return "Not Applicable"
    if isinstance(severity_mappings, str): return severity_mappings
    for threshold, level in severity_mappings:
        if confidence >= threshold: return level
    return "Undetermined"

@app.route('/api/analyze', methods=['POST'])
def analyze_image():
    fundus_path, oct_path = None, None
    try:
        patient_data = {k: request.form.get(k) for k in ['name', 'age', 'gender', 'diabetesType', 'diabetesDuration', 'phone', 'email']}
        patient_data['symptoms'] = request.form.getlist('symptoms[]'); results = {}
        if 'fundusImage' in request.files:
            fundus_file = request.files['fundusImage']
            if fundus_file and allowed_file(fundus_file.filename):
                fundus_filename = secure_filename(f"fundus_{fundus_file.filename}"); fundus_path = os.path.join(app.config['UPLOAD_FOLDER'], fundus_filename)
                fundus_file.save(fundus_path); disease, conf, severity, heatmap, original = predict(fundus_model, fundus_path, 'fundus', Config.FUNDUS_CLASSES)
                results['fundus'] = {'disease': disease, 'confidence': round(conf * 100, 2), 'severity': severity, 'heatmap_b64': heatmap, 'original_b64': original}
        if 'octImage' in request.files:
            oct_file = request.files['octImage']
            if oct_file and allowed_file(oct_file.filename):
                oct_filename = secure_filename(f"oct_{oct_file.filename}"); oct_path = os.path.join(app.config['UPLOAD_FOLDER'], oct_filename)
                oct_file.save(oct_path); disease, conf, severity, heatmap, original = predict(oct_model, oct_path, 'oct', Config.OCT_CLASSES)
                results['oct'] = {'disease': disease, 'confidence': round(conf * 100, 2), 'severity': severity, 'heatmap_b64': heatmap, 'original_b64': original}
        if not results: return jsonify({'error': 'No valid images provided.'}), 400
        recommendations = gemini_api.get_recommendations(patient_data, results)
        report_filename = pdf_generator.generate_report(patient_data, results, recommendations)
        return jsonify({'success': True, 'results': results, 'recommendations': recommendations, 'report_url': f'/api/download-report/{report_filename}'})
    except Exception as e:
        print(f"Error in /api/analyze: {e}"); return jsonify({'error': 'An internal server error occurred.'}), 500
    finally:
        if fundus_path and os.path.exists(fundus_path): os.remove(fundus_path)
        if oct_path and os.path.exists(oct_path): os.remove(oct_path)

@app.route('/api/explain', methods=['POST'])
def explain_disease():
    data = request.get_json()
    disease_name = data.get('disease')
    if not disease_name:
        return jsonify({'error': 'Disease name not provided.'}), 400
    try:
        explanation = gemini_api.get_disease_explanation(disease_name)
        return jsonify({'explanation': explanation})
    except Exception as e:
        print(f"Error in /api/explain: {e}")
        return jsonify({'error': 'Failed to generate explanation.'}), 500

@app.route('/api/download-report/<filename>')
def download_report(filename): return send_from_directory(app.config['REPORTS_FOLDER'], filename, as_attachment=True)

@app.route('/api/health')
def health_check(): return jsonify({'status': 'healthy', 'fundus_model_loaded': fundus_model is not None, 'oct_model_loaded': oct_model is not None})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
