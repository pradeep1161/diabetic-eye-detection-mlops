import os, argparse, sys, hashlib, mlflow, mlflow.keras, numpy as np, pandas as pd, tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import EfficientNetV2B0
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import accuracy_score
from PIL import Image

def validate_dataset(directory):
    print(f"\n--- Starting Validation for: {directory} ---")
    stats, seen_hashes, is_valid = [], {}, True
    for class_name in sorted(os.listdir(directory)):
        class_path = os.path.join(directory, class_name)
        if not os.path.isdir(class_path): continue
        valid_count, corrupted_count, duplicate_count = 0, 0, 0
        image_files = [f for f in os.listdir(class_path) if f.lower().endswith(('png', 'jpg', 'jpeg'))]
        for filename in image_files:
            filepath = os.path.join(class_path, filename)
            try:
                with Image.open(filepath) as img: img.verify()
                with open(filepath, 'rb') as f: file_hash = hashlib.md5(f.read()).hexdigest()
                if file_hash in seen_hashes:
                    print(f"  [DUPLICATE] {filename} is a duplicate of {seen_hashes[file_hash]}")
                    duplicate_count += 1; is_valid = False
                else:
                    seen_hashes[file_hash] = filename; valid_count += 1
            except Exception as e:
                print(f"  [CORRUPTED] {filename}: {e}"); corrupted_count += 1; is_valid = False
        stats.append({"Class": class_name, "Valid": valid_count, "Corrupted": corrupted_count, "Duplicates": duplicate_count})
    print("\n--- DATASET VALIDATION SUMMARY ---"); print(pd.DataFrame(stats).to_string(index=False))
    if not is_valid: print("\n❌ Validation Failed: Please clean the dataset.")
    else: print("\n✅ Validation Passed.")
    return is_valid

class EyeDiseaseModelTrainer:
    def __init__(self, config):
        self.config = config; self.img_size = (224, 224); self.batch_size = 32
        self.num_classes = len(config['classes']); self.model = None; self.base_model = None
    def prepare_data(self):
        train_datagen = ImageDataGenerator(rotation_range=20, width_shift_range=0.2, height_shift_range=0.2, horizontal_flip=True, zoom_range=0.2, shear_range=0.2, fill_mode='nearest', preprocessing_function=tf.keras.applications.efficientnet_v2.preprocess_input)
        val_datagen = ImageDataGenerator(preprocessing_function=tf.keras.applications.efficientnet_v2.preprocess_input)
        self.train_generator = train_datagen.flow_from_directory(os.path.join(self.config['dataset_path'], 'train'), target_size=self.img_size, batch_size=self.batch_size, class_mode='categorical', shuffle=True, classes=self.config['classes'])
        self.val_generator = val_datagen.flow_from_directory(os.path.join(self.config['dataset_path'], 'validation'), target_size=self.img_size, batch_size=self.batch_size, class_mode='categorical', shuffle=False, classes=self.config['classes'])
    def build_model(self):
        self.base_model = EfficientNetV2B0(input_shape=(*self.img_size, 3), include_top=False, weights='imagenet')
        self.base_model.trainable = False
        inputs = tf.keras.Input(shape=(*self.img_size, 3)); x = self.base_model(inputs, training=False)
        x = layers.GlobalAveragePooling2D()(x); x = layers.BatchNormalization()(x)
        x = layers.Dense(256, activation='relu')(x); x = layers.Dropout(0.5)(x)
        outputs = layers.Dense(self.num_classes, activation='softmax')(x)
        self.model = models.Model(inputs, outputs)
    def train(self, epochs=25, fine_tune_epochs=15):
        mlflow.set_experiment(self.config['experiment_name'])
        with mlflow.start_run() as run:
            print(f"--- Starting MLflow Run: {run.info.run_id} ---")
            mlflow.log_params({"model_type": self.config['type'], "image_size": self.img_size[0], "batch_size": self.batch_size})
            self.model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss='categorical_crossentropy', metrics=['accuracy'])
            self.model.fit(self.train_generator, epochs=epochs, validation_data=self.val_generator, callbacks=[EarlyStopping(patience=10, restore_best_weights=True)], verbose=1)
            self.base_model.trainable = True
            for layer in self.base_model.layers[:-30]: layer.trainable = False
            self.model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5), loss='categorical_crossentropy', metrics=['accuracy'])
            self.model.fit(self.train_generator, epochs=fine_tune_epochs, validation_data=self.val_generator, verbose=1)
            
            # --- Final Evaluation ---
            predictions = self.model.predict(self.val_generator)
            y_pred = np.argmax(predictions, axis=1)
            # CORRECTED: Use .labels to get the ground truth in the correct order
            y_true = self.val_generator.labels 
            
            accuracy = accuracy_score(y_true, y_pred)
            mlflow.log_metric("val_accuracy", accuracy)
            mlflow.keras.log_model(self.model, artifact_path="model", registered_model_name=self.config['registered_model_name'])
            print(f"--- Final Validation Accuracy: {accuracy:.4f} ---")
            print("--- MLflow Run Complete ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate and train an eye disease model.")
    parser.add_argument('--type', type=str, required=True, choices=['fundus', 'oct'])
    args = parser.parse_args()
    model_configs = {
        'fundus': {'type': 'fundus', 'dataset_path': '../dataset/fundus', 'experiment_name': 'Diabetic Eye - Fundus', 'registered_model_name': 'fundus-model', 'classes': ['normal', 'diabetic_retinopathy', 'cataracts', 'glaucoma']},
        'oct': {'type': 'oct', 'dataset_path': '../dataset/oct', 'experiment_name': 'Diabetic Eye - OCT', 'registered_model_name': 'oct-model', 'classes': ['normal', 'macular_edema']}
    }
    config = model_configs[args.type]
    
    # The DVC pull is handled by the GitHub Actions workflow, so it is removed from this script.
    
    if validate_dataset(os.path.join(config['dataset_path'], 'train')) and validate_dataset(os.path.join(config['dataset_path'], 'validation')):
        print(f"\n--- Proceeding with training for model type: {args.type.upper()} ---")
        trainer = EyeDiseaseModelTrainer(config); trainer.prepare_data(); trainer.build_model(); trainer.train()
    else:
        print("\n--- Halting execution due to data validation errors. ---"); sys.exit(1)
