import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    UPLOAD_FOLDER = os.path.abspath('temp')
    REPORTS_FOLDER = os.path.abspath('../reports')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    IMAGE_SIZE = (224, 224)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    FUNDUS_MODEL_PATH = 'models/fundus_model.h5'
    FUNDUS_CLASSES = ['normal', 'diabetic_retinopathy', 'cataracts', 'glaucoma']
    OCT_MODEL_PATH = 'models/oct_model.h5'
    OCT_CLASSES = ['normal', 'macular_edema']
    SEVERITY_LEVELS = {
        'fundus': {
            'normal': 'No Disease Detected',
            'diabetic_retinopathy': [(0.8, 'Proliferative'), (0.6, 'Severe'), (0.3, 'Moderate'), (0.0, 'Mild')],
            'cataracts': [(0.7, 'Advanced'), (0.4, 'Moderate'), (0.0, 'Early')],
            'glaucoma': [(0.8, 'Severe'), (0.6, 'Moderate'), (0.3, 'Mild'), (0.0, 'Suspected')]
        },
        'oct': {
            'normal': 'No Disease Detected',
            'macular_edema': [(0.7, 'Advanced'), (0.4, 'Moderate'), (0.0, 'Early Stage')]
        }
    }
